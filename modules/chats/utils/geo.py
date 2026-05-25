import logging

from modules.chats.services import update_messages_geo_data
from modules.users.models import User
from modules.users.services import update_user_geo_data
from modules.utils.database import async_session


logger = logging.getLogger(__name__)


async def backfill_user_and_messages_geo(user_id: int, geo_data: dict[str, str | None]) -> None:
    """Persist a fresh geo lookup onto an existing user and their messages.

    Runs as a FastAPI BackgroundTask after the response has been streamed,
    so the request path itself never waits on the DB writes. Only invoked
    when the user previously had no geo data and the IP lookup just
    returned at least one populated field.
    """
    if not any(geo_data.values()):
        return

    try:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user is None:
                return

            if not any([user.country, user.region, user.city]):
                await update_user_geo_data(
                    session,
                    user,
                    geo_data["country"],
                    geo_data["region"],
                    geo_data["city"],
                )

            await update_messages_geo_data(
                session,
                user_id,
                geo_data["country"],
                geo_data["region"],
                geo_data["city"],
            )
    except Exception:
        logger.exception("Geo backfill failed for user %s", user_id)
