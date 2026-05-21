from sqlmodel import select

from modules.chats.services import update_messages_geo_data
from modules.users.models import User
from modules.users.services import update_user_geo_data
from modules.utils.database import async_session


async def update_user_and_messages_geo_background(
    user_id: int,
    user_country: str | None,
    user_region: str | None,
    user_city: str | None,
    geo_data: dict,
):
    """Background task to update user and message geo data if they don't have it but request does."""
    try:
        # Create a new session for the background task
        async with async_session() as session:
            user_has_geo = any([user_country, user_region, user_city])
            request_has_geo = any([geo_data["country"], geo_data["region"], geo_data["city"]])

            final_geo_for_update = None

            if not user_has_geo and request_has_geo:
                final_geo_for_update = geo_data
            elif user_has_geo and not request_has_geo:
                final_geo_for_update = {
                    "country": user_country,
                    "region": user_region,
                    "city": user_city,
                }

            if final_geo_for_update:
                if not user_has_geo and request_has_geo:
                    # We need to fetch the user again in this new session
                    statement = select(User).where(User.id == user_id)
                    result = await session.exec(statement)
                    user = result.first()

                    if user:
                        await update_user_geo_data(
                            session,
                            user,
                            final_geo_for_update["country"],
                            final_geo_for_update["region"],
                            final_geo_for_update["city"],
                        )

                await update_messages_geo_data(
                    session,
                    user_id,
                    final_geo_for_update["country"],
                    final_geo_for_update["region"],
                    final_geo_for_update["city"],
                )
    except Exception:
        pass
