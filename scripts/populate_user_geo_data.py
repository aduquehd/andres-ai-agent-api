import asyncio
import sys
from datetime import datetime
from pathlib import Path


# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from modules.chats.models import AgentMessage, Message  # noqa
from modules.users.models import User
from modules.utils.database import async_session
from modules.utils.geo import get_geographic_data


async def get_users_without_geo_data(db: AsyncSession) -> list[User]:
    """Get all users that don't have complete geographic data."""
    result = await db.exec(
        select(User).where(
            (User.country.is_(None)) | (User.region.is_(None)) | (User.city.is_(None))
        )
    )
    return result.all()


async def update_user_geo_data(db: AsyncSession, user: User) -> bool:
    """Update geographic data for a single user."""
    if not user.ip_address or user.ip_address == "unknown":
        return False

    geo_data = get_geographic_data(user.ip_address)
    print(f"  Geo data result: {geo_data}")

    if geo_data["country"] or geo_data["region"] or geo_data["city"]:
        user.country = geo_data["country"]
        user.region = geo_data["region"]
        user.city = geo_data["city"]

        db.add(user)
        await db.commit()

        return True
    else:
        return False


async def main():
    """Main function to populate geo data for all users."""
    async with async_session() as db:
        users_without_geo = await get_users_without_geo_data(db)

        if not users_without_geo:
            print("No users found without geographic data.")
            return

        print(f"Found {len(users_without_geo)} users without complete geo data.")

        updated_count = 0
        failed_count = 0

        for i, user in enumerate(users_without_geo, 1):
            print(
                f"\nProcessing user {i}/{len(users_without_geo)}: {user.username} (IP: {user.ip_address})"
            )

            if await update_user_geo_data(db, user):
                updated_count += 1
            else:
                failed_count += 1

            # Add a small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        print("\n--- Summary ---")
        print(f"Total users processed: {len(users_without_geo)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Failed to update: {failed_count}")


if __name__ == "__main__":
    print("Starting geographic data population...")
    print(f"Timestamp: {datetime.now()}")
    asyncio.run(main())
