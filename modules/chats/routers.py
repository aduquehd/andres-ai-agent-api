import json
import time
from datetime import datetime, timezone
from typing import Annotated

import logfire
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import Response, StreamingResponse
from fastapi_limiter.depends import RateLimiter
from openai import AsyncOpenAI
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelResponse,
    TextPart,
)
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.agent.agent import agent
from modules.chats.models import AgentMessage, Message, MessageDirectionEnum
from modules.chats.services import add_agent_message, add_message
from modules.chats.utils.geo import update_user_and_messages_geo_background
from modules.users.models import User
from modules.users.services import create_user, get_user_by_username
from modules.utils.agent import Deps, to_chat_message
from modules.utils.auth import get_user_id_from_auth_header
from modules.utils.database import get_session
from modules.utils.geo import get_geographic_data
from modules.utils.rate_limit import get_client_ip_identifier
from modules.utils.request import get_browser_id, get_client_ip, get_user_agent


router = APIRouter()


async def _get_user_geo_data(
    user: User | None,
    client_ip: str,
    background_tasks: BackgroundTasks,
) -> dict[str, str | None]:
    """Get or update user geographic data.

    Returns a dict with country, region, and city keys.
    If user exists and has geo data, returns user's data.
    If user exists but lacks geo data, fetches it and schedules background update.
    If user doesn't exist, fetches geo data from IP.
    """
    if user:
        if not any([user.country, user.region, user.city]):
            geo_data = get_geographic_data(client_ip)
            background_tasks.add_task(
                update_user_and_messages_geo_background,
                user.id,
                user.country,
                user.region,
                user.city,
                geo_data,
            )
        else:
            geo_data = {
                "country": user.country,
                "region": user.region,
                "city": user.city,
            }
    else:
        geo_data = get_geographic_data(client_ip)

    return geo_data


@router.get(
    "/history",
    dependencies=[Depends(RateLimiter(times=100, seconds=60, identifier=get_client_ip_identifier))],
)
async def get_chat(
    user_id: Annotated[str, Depends(get_user_id_from_auth_header)],
    session: AsyncSession = Depends(get_session),
) -> Response:
    user = await get_user_by_username(session, user_id)

    if not user:
        return Response(b"", media_type="text/plain")

    query = (
        select(AgentMessage).where(AgentMessage.user_id == user.id).order_by(AgentMessage.id.asc())
    )
    result = await session.exec(query)
    messages = result.all()

    list_messages: list[ModelMessage] = []
    for message in messages:
        list_messages.extend(ModelMessagesTypeAdapter.validate_json(message.message_list))

    lines = []
    for message in list_messages:
        chat_msg = to_chat_message(message)
        if chat_msg:
            json_str = json.dumps(chat_msg)
            lines.append(json_str.encode("utf-8"))

    return Response(b"\n".join(lines), media_type="text/plain")


@router.post(
    "/send",
    dependencies=[Depends(RateLimiter(times=30, seconds=60, identifier=get_client_ip_identifier))],
)
async def post_chat(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: Annotated[str, Depends(get_user_id_from_auth_header)],
    prompt: Annotated[str, Form()],
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    user = await get_user_by_username(session, user_id)
    now = datetime.now(timezone.utc)
    start_time = time.time()

    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    browser_id = get_browser_id(request)

    geo_data = await _get_user_geo_data(user, client_ip, background_tasks)

    if not user:
        user = User(
            username=user_id,
            browser_id=browser_id,
            ip_address=client_ip,
            user_agent=user_agent,
            country=geo_data["country"],
            region=geo_data["region"],
            city=geo_data["city"],
        )
        user = await create_user(session, user)

    async def stream_messages():
        """Streams new line delimited JSON Messages to the client."""
        # stream the user prompt so that can be displayed straight away
        yield (
            json.dumps(
                {
                    "role": "user",
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "content": prompt,
                }
            ).encode("utf-8")
            + b"\n"
        )

        openai = AsyncOpenAI()
        logfire.instrument_openai(openai)

        logfire.info('Asking "{question}" from user {user_id}', question=prompt, user_id=user_id)

        query = select(AgentMessage).where(AgentMessage.user_id == user.id)
        result = await session.exec(query)
        messages = result.all()

        list_messages: list[ModelMessage] = []
        for message in messages:
            list_messages.extend(ModelMessagesTypeAdapter.validate_json(message.message_list))

        deps = Deps(openai=openai, session=session)

        async with agent.run_stream(prompt, message_history=list_messages, deps=deps) as result:
            async for text in result.stream(debounce_by=0.01):
                # text here is a str and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                agent_response = to_chat_message(m)

                yield json.dumps(agent_response).encode("utf-8") + b"\n"

        new_message_json = result.new_messages_json()
        agent_message = AgentMessage(
            user_id=user.id, message_list=new_message_json.decode("utf-8"), created_at=now
        )
        await add_agent_message(session, agent_message)

        # Calculate response time
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        end_datetime = datetime.now(timezone.utc)

        # Save user message (outgoing)
        new_message = Message(
            message=prompt,
            user_id=user.id,
            created_at=now,
            direction=MessageDirectionEnum.outgoing,
            ip_address=client_ip,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            country=geo_data["country"],
            region=geo_data["region"],
            city=geo_data["city"],
        )
        await add_message(session, new_message)

        # Save agent response (incoming)
        new_message = Message(
            message=agent_response["content"],
            user_id=user.id,
            created_at=end_datetime,  # Use end time for agent response
            direction=MessageDirectionEnum.incoming,
            ip_address=client_ip,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            country=geo_data["country"],
            region=geo_data["region"],
            city=geo_data["city"],
        )
        await add_message(session, new_message)

    return StreamingResponse(
        stream_messages(),
        media_type="text/plain",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # CloudFlare specific headers to disable buffering
            "CF-Cache-Status": "DYNAMIC",
            "CF-Cache-Level": "bypass",
        },
    )
