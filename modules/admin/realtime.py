"""In-memory pub/sub for the admin WebSocket stream.

Each connected WebSocket subscribes a small bounded ``asyncio.Queue``; producers
call :func:`publish` to fan an event out to every active subscriber. A bounded
queue means a stalled client cannot grow memory without limit — when the queue
overflows we drop the slow consumer rather than back-pressure producers.

This is intentionally an in-process broadcaster — the API runs as a single
backend container (see docker-compose.prod.yml), so cross-process pub/sub via
Redis is not yet required.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from modules.chats.models import Message
    from modules.users.models import User

log = logging.getLogger(__name__)

# Per-subscriber queue size. Generous — chat traffic produces at most a couple
# of events per user turn — but bounded so a stuck client cannot leak memory.
_QUEUE_SIZE = 256


class AdminBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_SIZE)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        """Fan an event out to every active subscriber without awaiting them.

        Safe to call from sync code paths. A subscriber whose queue is full is
        evicted: that subscriber's WebSocket consumer was too slow, and keeping
        it would block the rest of the broadcast loop.
        """
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                log.warning("admin broadcaster: dropping slow subscriber")
                dead.append(queue)
        for queue in dead:
            self._subscribers.discard(queue)


broadcaster = AdminBroadcaster()


def serialize_user(user: User) -> dict[str, Any]:
    """Shape a User into the same wire format the admin REST endpoints emit."""
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


def serialize_message(message: Message) -> dict[str, Any]:
    """Shape a Message into the same wire format the admin REST endpoints emit."""
    return {
        "id": message.id,
        "user_id": message.user_id,
        "message": message.message,
        "direction": message.direction.value if message.direction else None,
        "ip_address": message.ip_address,
        "user_agent": message.user_agent,
        "country": message.country,
        "region": message.region,
        "city": message.city,
        "response_time_ms": message.response_time_ms,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def publish_user_created(user: User) -> None:
    broadcaster.publish({"type": "user.created", "user": serialize_user(user)})


def publish_message_created(message: Message) -> None:
    broadcaster.publish({"type": "message.created", "message": serialize_message(message)})
