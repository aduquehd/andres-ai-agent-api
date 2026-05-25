from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from modules.agent.models import AgentContext


async def get_agent_context(session: AsyncSession) -> str:
    query = (
        select(AgentContext)
        .where(AgentContext.status.is_(True))
        .order_by(desc(AgentContext.created_at))
        .limit(1)
    )

    result = await session.exec(query)
    agent_context = result.first()

    if not agent_context or not agent_context.agent_prompt:
        return ""

    return agent_context.agent_prompt
