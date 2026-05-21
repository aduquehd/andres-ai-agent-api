from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from modules.chats.models import AgentMessage, Message


async def add_message(session: AsyncSession, message: Message) -> Message:
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def add_agent_message(session: AsyncSession, agent_message: AgentMessage) -> AgentMessage:
    session.add(agent_message)
    await session.commit()
    await session.refresh(agent_message)
    return agent_message


async def get_agent_messages(
    session: AsyncSession,
    user_id: int,
):
    query = (
        select(AgentMessage).where(AgentMessage.user_id == user_id).order_by(AgentMessage.id.asc())
    )
    result = await session.exec(query)
    return result.all()


async def update_messages_geo_data(
    session: AsyncSession, user_id: int, country: str | None, region: str | None, city: str | None
) -> int:
    """Update messages without geo data for a specific user."""
    stmt = (
        update(Message)
        .where(
            Message.user_id == user_id,
            Message.country.is_(None),
            Message.region.is_(None),
            Message.city.is_(None),
        )
        .values(country=country, region=region, city=city)
    )

    await session.exec(stmt)
    await session.commit()
