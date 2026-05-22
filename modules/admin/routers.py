"""JSON admin API consumed by the Next.js admin UI."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import and_, cast, delete, func, or_
from sqlalchemy.types import Date
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.admin.auth import (
    ADMIN_COOKIE_NAME,
    ADMIN_TOKEN_TTL_HOURS,
    create_admin_token,
    decode_admin_token,
    require_admin,
    verify_admin_credentials,
)
from modules.admin.realtime import broadcaster
from modules.agent.models import AgentContext
from modules.chats.models import AgentMessage, Message, MessageDirectionEnum
from modules.knowledge_base.models import KnowledgeBase, KnowledgeBaseTypeEnum
from modules.users.models import User
from modules.utils.database import get_session


log = logging.getLogger(__name__)


router = APIRouter(prefix="/api/admin")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


# -------------------------------------------------------------------- auth ---


class LoginPayload(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    username: str


@router.post("/login")
async def login(payload: LoginPayload, response: Response) -> MeResponse:
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_admin_token(payload.username)
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=ADMIN_TOKEN_TTL_HOURS * 3600,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return MeResponse(username=payload.username)


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        secure=True,
        samesite="none",
    )
    return {"ok": True}


@router.get("/me")
async def me(username: Annotated[str, Depends(require_admin)]) -> MeResponse:
    return MeResponse(username=username)


# --------------------------------------------------------------- realtime ---

# WebSocket close codes (4xxx range is reserved for app-defined values)
WS_AUTH_REQUIRED = 4401


@router.websocket("/ws")
async def admin_ws(websocket: WebSocket) -> None:
    """Authenticated event stream for the admin UI.

    Authentication reuses the admin JWT cookie (``admin_session``). The browser
    sends the cookie automatically on the WebSocket handshake when the cookie's
    SameSite policy allows it (set to ``None`` in :func:`login`).
    """
    token = websocket.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        await websocket.close(code=WS_AUTH_REQUIRED)
        return
    try:
        payload = decode_admin_token(token)
    except jwt.PyJWTError:
        await websocket.close(code=WS_AUTH_REQUIRED)
        return
    if payload.get("scope") != "admin":
        await websocket.close(code=WS_AUTH_REQUIRED)
        return

    await websocket.accept()
    queue = await broadcaster.subscribe()
    try:
        # A short hello so the client can confirm the connection is live.
        await websocket.send_json({"type": "hello", "username": payload.get("sub", "")})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        log.exception("admin ws: send loop crashed")
    finally:
        await broadcaster.unsubscribe(queue)


# -------------------------------------------------------------- dashboard ---


MESSAGES_RANGES = {"this_month", "30d", "60d", "90d", "all"}


def _resolve_messages_range(
    messages_range: str, today_start: datetime, earliest: datetime | None
) -> tuple[datetime, int]:
    """Return (start_datetime, day_count) for the chart based on the selected range."""
    if messages_range == "this_month":
        start = today_start.replace(day=1)
    elif messages_range == "30d":
        start = today_start - timedelta(days=29)
    elif messages_range == "60d":
        start = today_start - timedelta(days=59)
    elif messages_range == "90d":
        start = today_start - timedelta(days=89)
    else:  # "all"
        start = earliest.replace(hour=0, minute=0, second=0, microsecond=0) if earliest else today_start
    day_count = max(1, (today_start.date() - start.date()).days + 1)
    return start, day_count


@router.get("/dashboard/stats", dependencies=[Depends(require_admin)])
async def dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    messages_range: str = "all",
) -> dict[str, Any]:
    """Aggregate metrics powering the admin dashboard.

    The ``messages_range`` query controls the throughput chart bucket span:
    one of ``this_month``, ``30d``, ``60d``, ``90d``, or ``all`` (default).
    Other metrics (totals, latency, etc.) are not affected by this filter.
    """
    if messages_range not in MESSAGES_RANGES:
        messages_range = "all"
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # ----- Totals (one query each, count) -----
    users_total = int((await session.exec(select(func.count()).select_from(User))).one())
    messages_total = int(
        (await session.exec(select(func.count()).select_from(Message))).one()
    )
    kb_total = int(
        (await session.exec(select(func.count()).select_from(KnowledgeBase))).one()
    )
    agent_ctx_total = int(
        (await session.exec(select(func.count()).select_from(AgentContext))).one()
    )

    # ----- Today bucket -----
    messages_today = int(
        (
            await session.exec(
                select(func.count())
                .select_from(Message)
                .where(Message.created_at >= today_start)
            )
        ).one()
    )
    active_users_today = int(
        (
            await session.exec(
                select(func.count(func.distinct(Message.user_id))).where(
                    Message.created_at >= today_start
                )
            )
        ).one()
    )
    avg_latency_today_row = (
        await session.exec(
            select(func.avg(Message.response_time_ms)).where(
                Message.created_at >= today_start,
                Message.response_time_ms.is_not(None),
            )
        )
    ).one()
    avg_latency_today = (
        float(avg_latency_today_row) if avg_latency_today_row is not None else None
    )

    # ----- Messages per day for the selected range, split by direction -----
    earliest = (
        await session.exec(select(func.min(Message.created_at)))
    ).one()
    range_start, day_count = _resolve_messages_range(messages_range, today_start, earliest)
    day_col = cast(Message.created_at, Date).label("day")
    rows = (
        await session.exec(
            select(
                day_col,
                Message.direction,
                func.count().label("count"),
            )
            .where(Message.created_at >= range_start)
            .group_by(day_col, Message.direction)
            .order_by(day_col.asc())
        )
    ).all()
    # Bucket the rows into per-day {incoming, outgoing} pairs, filling gaps with zero.
    buckets: dict[str, dict[str, int]] = {}
    for day, direction, count in rows:
        key = day.isoformat() if hasattr(day, "isoformat") else str(day)
        bucket = buckets.setdefault(key, {"incoming": 0, "outgoing": 0})
        if direction is not None:
            bucket[direction.value] = int(count)
    messages_by_day: list[dict[str, Any]] = []
    for i in range(day_count):
        d = (range_start + timedelta(days=i)).date()
        key = d.isoformat()
        b = buckets.get(key, {"incoming": 0, "outgoing": 0})
        messages_by_day.append(
            {"date": key, "incoming": b["incoming"], "outgoing": b["outgoing"]}
        )

    # ----- Top countries (top 10 by message count) -----
    country_rows = (
        await session.exec(
            select(Message.country, func.count().label("count"))
            .where(Message.country.is_not(None))
            .group_by(Message.country)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    messages_by_country = [
        {"country": c, "count": int(n)} for c, n in country_rows if c
    ]

    # ----- Overall direction split -----
    direction_rows = (
        await session.exec(
            select(Message.direction, func.count().label("count")).group_by(
                Message.direction
            )
        )
    ).all()
    direction_split = {"incoming": 0, "outgoing": 0}
    for d, n in direction_rows:
        if d is not None:
            direction_split[d.value] = int(n)

    # ----- Latency percentiles (Postgres-only via percentile_cont) -----
    latency: dict[str, float | None] = {"avg": None, "p50": None, "p95": None, "p99": None}
    if messages_total > 0:
        latency_row = (
            await session.exec(
                select(
                    func.avg(Message.response_time_ms),
                    func.percentile_cont(0.5).within_group(
                        Message.response_time_ms.asc()
                    ),
                    func.percentile_cont(0.95).within_group(
                        Message.response_time_ms.asc()
                    ),
                    func.percentile_cont(0.99).within_group(
                        Message.response_time_ms.asc()
                    ),
                ).where(Message.response_time_ms.is_not(None))
            )
        ).one()
        avg_v, p50_v, p95_v, p99_v = latency_row
        latency = {
            "avg": float(avg_v) if avg_v is not None else None,
            "p50": float(p50_v) if p50_v is not None else None,
            "p95": float(p95_v) if p95_v is not None else None,
            "p99": float(p99_v) if p99_v is not None else None,
        }

    return {
        "totals": {
            "users": users_total,
            "messages": messages_total,
            "kb_entries": kb_total,
            "agent_contexts": agent_ctx_total,
        },
        "today": {
            "messages": messages_today,
            "active_users": active_users_today,
            "avg_latency_ms": avg_latency_today,
        },
        "messages_by_day": messages_by_day,
        "messages_range": messages_range,
        "messages_by_country": messages_by_country,
        "direction_split": direction_split,
        "latency": latency,
        "generated_at": now.isoformat(),
    }


# ---------------------------------------------------------------- helpers ---


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "browser_id": user.browser_id,
        "ip_address": user.ip_address,
        "user_agent": user.user_agent,
        "country": user.country,
        "region": user.region,
        "city": user.city,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _message_to_dict(m: Message) -> dict[str, Any]:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "message": m.message,
        "direction": m.direction.value if m.direction else None,
        "ip_address": m.ip_address,
        "user_agent": m.user_agent,
        "country": m.country,
        "region": m.region,
        "city": m.city,
        "response_time_ms": m.response_time_ms,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _agent_message_to_dict(m: AgentMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "message_list": m.message_list,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _knowledge_base_to_dict(k: KnowledgeBase) -> dict[str, Any]:
    return {
        "id": k.id,
        "type": k.type.value if k.type else None,
        "title": k.title,
        "content": k.content,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


def _agent_context_to_dict(a: AgentContext) -> dict[str, Any]:
    return {
        "id": a.id,
        "status": a.status,
        "agent_prompt": a.agent_prompt,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


async def _count(session: AsyncSession, model: Any, where=None) -> int:
    stmt = select(func.count()).select_from(model)
    if where is not None:
        stmt = stmt.where(where)
    result = await session.exec(stmt)
    return int(result.one())


def _clamp_limit(limit: int) -> int:
    if limit <= 0:
        return DEFAULT_PAGE_SIZE
    return min(limit, MAX_PAGE_SIZE)


# ------------------------------------------------------------------ users ---


@router.get(
    "/users",
    dependencies=[Depends(require_admin)],
)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    limit = _clamp_limit(limit)
    stmt = select(User).order_by(User.created_at.desc())
    where = None
    if q:
        like = f"%{q}%"
        where = or_(
            User.username.ilike(like),
            User.browser_id.ilike(like),
            User.ip_address.ilike(like),
            User.country.ilike(like),
            User.city.ilike(like),
        )
        stmt = stmt.where(where)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.exec(stmt)).all()
    total = await _count(session, User, where)
    return {
        "items": [_user_to_dict(u) for u in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/{user_id}", dependencies=[Depends(require_admin)])
async def get_user(
    user_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.get("/users/{user_id}/stats", dependencies=[Depends(require_admin)])
async def get_user_stats(
    user_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    """User profile plus aggregate activity counts and date range."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    direction_rows = (
        await session.exec(
            select(Message.direction, func.count().label("count"))
            .where(Message.user_id == user_id)
            .group_by(Message.direction)
        )
    ).all()
    incoming = 0
    outgoing = 0
    for d, n in direction_rows:
        if d == MessageDirectionEnum.incoming:
            incoming = int(n)
        elif d == MessageDirectionEnum.outgoing:
            outgoing = int(n)

    agent_messages_total = int(
        (
            await session.exec(
                select(func.count())
                .select_from(AgentMessage)
                .where(AgentMessage.user_id == user_id)
            )
        ).one()
    )

    range_row = (
        await session.exec(
            select(
                func.min(Message.created_at),
                func.max(Message.created_at),
                func.avg(Message.response_time_ms),
            ).where(Message.user_id == user_id)
        )
    ).one()
    first_at, last_at, avg_latency = range_row

    return {
        "user": _user_to_dict(user),
        "messages_total": incoming + outgoing,
        "messages_incoming": incoming,
        "messages_outgoing": outgoing,
        "agent_messages_total": agent_messages_total,
        "first_message_at": first_at.isoformat() if first_at else None,
        "last_message_at": last_at.isoformat() if last_at else None,
        "avg_response_time_ms": float(avg_latency) if avg_latency is not None else None,
    }


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    """Delete a user and cascade-remove all their messages and agent messages."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    messages_deleted = int(
        (
            await session.exec(
                select(func.count())
                .select_from(Message)
                .where(Message.user_id == user_id)
            )
        ).one()
    )
    agent_messages_deleted = int(
        (
            await session.exec(
                select(func.count())
                .select_from(AgentMessage)
                .where(AgentMessage.user_id == user_id)
            )
        ).one()
    )
    await session.exec(delete(Message).where(Message.user_id == user_id))
    await session.exec(delete(AgentMessage).where(AgentMessage.user_id == user_id))
    await session.delete(user)
    await session.commit()
    broadcaster.publish(
        {
            "type": "user.deleted",
            "id": user_id,
            "messages_deleted": messages_deleted,
            "agent_messages_deleted": agent_messages_deleted,
        }
    )
    return {
        "ok": True,
        "messages_deleted": messages_deleted,
        "agent_messages_deleted": agent_messages_deleted,
    }


# ---------------------------------------------------------- conversations ---


CONVERSATION_SORTS = {"last_activity_desc", "user_newest", "messages_desc"}


@router.get("/conversations", dependencies=[Depends(require_admin)])
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = None,
    sort: str = "last_activity_desc",
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    """One row per user-with-messages: counts, activity window, last-message preview.

    A 'conversation' here means the bundle of all messages exchanged with a
    single user, since each end-user is identified by a stable browser UUID
    (their ``users.username``). Users who have never sent a message are
    excluded.
    """
    if sort not in CONVERSATION_SORTS:
        sort = "last_activity_desc"
    limit = _clamp_limit(limit)

    # Per-user message aggregates. ``func.count().filter(...)`` emits Postgres
    # ``COUNT(*) FILTER (WHERE ...)`` — cleaner than a CASE expression.
    agg = (
        select(
            Message.user_id.label("user_id"),
            func.count().label("messages_total"),
            func.count()
            .filter(Message.direction == MessageDirectionEnum.incoming)
            .label("incoming"),
            func.count()
            .filter(Message.direction == MessageDirectionEnum.outgoing)
            .label("outgoing"),
            func.min(Message.created_at).label("first_at"),
            func.max(Message.created_at).label("last_at"),
        )
        .group_by(Message.user_id)
        .subquery()
    )

    stmt = select(
        User,
        agg.c.messages_total,
        agg.c.incoming,
        agg.c.outgoing,
        agg.c.first_at,
        agg.c.last_at,
    ).join(agg, agg.c.user_id == User.id)

    where = None
    if q:
        like = f"%{q}%"
        where = or_(
            User.username.ilike(like),
            User.browser_id.ilike(like),
            User.ip_address.ilike(like),
            User.country.ilike(like),
            User.city.ilike(like),
        )
        stmt = stmt.where(where)

    if sort == "user_newest":
        stmt = stmt.order_by(User.created_at.desc())
    elif sort == "messages_desc":
        stmt = stmt.order_by(agg.c.messages_total.desc(), agg.c.last_at.desc())
    else:  # last_activity_desc
        stmt = stmt.order_by(agg.c.last_at.desc())

    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.exec(stmt)).all()

    # Fetch the preview (latest message) for each user shown.
    user_ids = [row[0].id for row in rows]
    previews: dict[int, dict[str, Any]] = {}
    if user_ids:
        # Postgres-specific DISTINCT ON for one query per user.
        preview_stmt = (
            select(Message)
            .where(Message.user_id.in_(user_ids))
            .order_by(Message.user_id, Message.created_at.desc())
            .distinct(Message.user_id)
        )
        for m in (await session.exec(preview_stmt)).all():
            previews[m.user_id] = {
                "message": m.message,
                "direction": m.direction.value if m.direction else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }

    # Total: number of distinct users that have at least one message (respecting q).
    if where is not None:
        total_stmt = (
            select(func.count(func.distinct(Message.user_id)))
            .select_from(Message)
            .join(User, Message.user_id == User.id)
            .where(where)
        )
    else:
        total_stmt = select(func.count(func.distinct(Message.user_id))).select_from(Message)
    total = int((await session.exec(total_stmt)).one())

    items = []
    for user, messages_total, incoming, outgoing, first_at, last_at in rows:
        items.append(
            {
                "user": _user_to_dict(user),
                "messages_total": int(messages_total),
                "messages_incoming": int(incoming or 0),
                "messages_outgoing": int(outgoing or 0),
                "first_message_at": first_at.isoformat() if first_at else None,
                "last_message_at": last_at.isoformat() if last_at else None,
                "preview": previews.get(user.id),
            }
        )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


# --------------------------------------------------------------- messages ---


MESSAGE_SORTS = {
    "created_desc": Message.created_at.desc(),
    "created_asc": Message.created_at.asc(),
}


@router.get("/messages/countries", dependencies=[Depends(require_admin)])
async def list_message_countries(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[str]:
    """Distinct non-null country codes present in messages, alphabetically sorted."""
    stmt = (
        select(Message.country)
        .where(Message.country.is_not(None))
        .distinct()
        .order_by(Message.country.asc())
    )
    rows = (await session.exec(stmt)).all()
    return [c for c in rows if c]


@router.get("/messages", dependencies=[Depends(require_admin)])
async def list_messages(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = None,
    user_id: int | None = None,
    direction: MessageDirectionEnum | None = None,
    country: str | None = None,
    sort: str = "created_desc",
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    limit = _clamp_limit(limit)
    order_by = MESSAGE_SORTS.get(sort, MESSAGE_SORTS["created_desc"])
    stmt = select(Message).order_by(order_by)
    conditions = []
    if user_id is not None:
        conditions.append(Message.user_id == user_id)
    if direction is not None:
        conditions.append(Message.direction == direction)
    if country:
        conditions.append(Message.country == country)
    if q:
        like = f"%{q}%"
        conditions.append(or_(Message.message.ilike(like), Message.ip_address.ilike(like)))
    where = None
    if conditions:
        where = and_(*conditions)
        stmt = stmt.where(where)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.exec(stmt)).all()
    total = await _count(session, Message, where)
    return {
        "items": [_message_to_dict(m) for m in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/messages/{message_id}", dependencies=[Depends(require_admin)])
async def get_message(
    message_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    m = await session.get(Message, message_id)
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    return _message_to_dict(m)


@router.delete("/messages/{message_id}", dependencies=[Depends(require_admin)])
async def delete_message(
    message_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    m = await session.get(Message, message_id)
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    user_id = m.user_id
    await session.delete(m)
    await session.commit()
    broadcaster.publish({"type": "message.deleted", "id": message_id, "user_id": user_id})
    return {"ok": True}


# --------------------------------------------------------- agent-messages ---


@router.get("/agent-messages", dependencies=[Depends(require_admin)])
async def list_agent_messages(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: int | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    limit = _clamp_limit(limit)
    stmt = select(AgentMessage).order_by(AgentMessage.created_at.desc())
    where = None
    if user_id is not None:
        where = AgentMessage.user_id == user_id
        stmt = stmt.where(where)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.exec(stmt)).all()
    total = await _count(session, AgentMessage, where)
    return {
        "items": [_agent_message_to_dict(m) for m in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/agent-messages/{message_id}", dependencies=[Depends(require_admin)])
async def get_agent_message(
    message_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    m = await session.get(AgentMessage, message_id)
    if not m:
        raise HTTPException(status_code=404, detail="Agent message not found")
    return _agent_message_to_dict(m)


@router.delete("/agent-messages/{message_id}", dependencies=[Depends(require_admin)])
async def delete_agent_message(
    message_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    m = await session.get(AgentMessage, message_id)
    if not m:
        raise HTTPException(status_code=404, detail="Agent message not found")
    await session.delete(m)
    await session.commit()
    return {"ok": True}


# ------------------------------------------------------- knowledge-base ---


class KnowledgeBasePayload(BaseModel):
    type: KnowledgeBaseTypeEnum
    title: str
    content: str


async def _compute_embedding(payload: KnowledgeBasePayload) -> list[float]:
    openai = AsyncOpenAI()
    text = f"type: {payload.type.value}\ntitle: {payload.title}\ncontent: {payload.content}"
    response = await openai.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding


@router.get("/knowledge-base", dependencies=[Depends(require_admin)])
async def list_knowledge_base(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    limit = _clamp_limit(limit)
    stmt = select(KnowledgeBase).order_by(KnowledgeBase.id.desc())
    where = None
    if q:
        like = f"%{q}%"
        where = or_(KnowledgeBase.title.ilike(like), KnowledgeBase.content.ilike(like))
        stmt = stmt.where(where)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await session.exec(stmt)).all()
    total = await _count(session, KnowledgeBase, where)
    return {
        "items": [_knowledge_base_to_dict(k) for k in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/knowledge-base/{kb_id}", dependencies=[Depends(require_admin)])
async def get_knowledge_base(
    kb_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    k = await session.get(KnowledgeBase, kb_id)
    if not k:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    return _knowledge_base_to_dict(k)


@router.post("/knowledge-base", dependencies=[Depends(require_admin)])
async def create_knowledge_base(
    payload: KnowledgeBasePayload,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    embedding = await _compute_embedding(payload)
    item = KnowledgeBase(
        type=payload.type,
        title=payload.title,
        content=payload.content,
        embedding=embedding,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _knowledge_base_to_dict(item)


@router.patch("/knowledge-base/{kb_id}", dependencies=[Depends(require_admin)])
async def update_knowledge_base(
    kb_id: int,
    payload: KnowledgeBasePayload,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    item = await session.get(KnowledgeBase, kb_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    embedding = await _compute_embedding(payload)
    item.type = payload.type
    item.title = payload.title
    item.content = payload.content
    item.embedding = embedding
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _knowledge_base_to_dict(item)


@router.delete("/knowledge-base/{kb_id}", dependencies=[Depends(require_admin)])
async def delete_knowledge_base(
    kb_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    item = await session.get(KnowledgeBase, kb_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge base entry not found")
    await session.delete(item)
    await session.commit()
    return {"ok": True}


# -------------------------------------------------------- agent-contexts ---


class AgentContextPayload(BaseModel):
    status: bool = False
    agent_prompt: str | None = None


@router.get("/agent-contexts", dependencies=[Depends(require_admin)])
async def list_agent_contexts(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, Any]:
    limit = _clamp_limit(limit)
    stmt = (
        select(AgentContext)
        .order_by(AgentContext.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.exec(stmt)).all()
    total = await _count(session, AgentContext)
    return {
        "items": [_agent_context_to_dict(a) for a in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/agent-contexts/{ctx_id}", dependencies=[Depends(require_admin)])
async def get_agent_context(
    ctx_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    a = await session.get(AgentContext, ctx_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent context not found")
    return _agent_context_to_dict(a)


@router.post("/agent-contexts", dependencies=[Depends(require_admin)])
async def create_agent_context(
    payload: AgentContextPayload,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    item = AgentContext(
        status=payload.status,
        agent_prompt=payload.agent_prompt,
        created_at=datetime.now(tz=timezone.utc),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return _agent_context_to_dict(item)


@router.patch("/agent-contexts/{ctx_id}", dependencies=[Depends(require_admin)])
async def update_agent_context(
    ctx_id: int,
    payload: AgentContextPayload,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    a = await session.get(AgentContext, ctx_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent context not found")
    a.status = payload.status
    a.agent_prompt = payload.agent_prompt
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return _agent_context_to_dict(a)


@router.delete("/agent-contexts/{ctx_id}", dependencies=[Depends(require_admin)])
async def delete_agent_context(
    ctx_id: int, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict:
    a = await session.get(AgentContext, ctx_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent context not found")
    await session.delete(a)
    await session.commit()
    return {"ok": True}
