from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from modules.users.models import User


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    result = await session.exec(statement)
    return result.first()


async def create_user(session: AsyncSession, user: User) -> User | None:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_geo_data(
    session: AsyncSession, user: User, country: str | None, region: str | None, city: str | None
) -> User:
    user.country = country
    user.region = region
    user.city = city
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
