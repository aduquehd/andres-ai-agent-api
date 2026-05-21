from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from modules.knowledge_base.models import KnowledgeBase, KnowledgeBaseTypeEnum


async def get_knowledge_base_list(
    session: AsyncSession, knowledge_base_type: str | None = None
) -> list[KnowledgeBase] | None:
    query = select(KnowledgeBase)
    if knowledge_base_type:
        query.where(KnowledgeBase.type == knowledge_base_type)
    result = await session.exec(query)
    return result.scalars().all()


async def add_knowledge_base(session: AsyncSession, knowledge_base: KnowledgeBase) -> KnowledgeBase:
    session.add(knowledge_base)
    await session.commit()
    await session.refresh(knowledge_base)
    return knowledge_base


async def delete_knowledge_base(session: AsyncSession, knowledge_base_id: int):
    statement = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    result = await session.exec(statement)
    instance = result.one_or_none()

    if not instance:
        return None

    await session.delete(instance)
    await session.commit()
    return instance.id


async def delete_all_knowledge_bases(session: AsyncSession):
    statement = delete(KnowledgeBase)
    await session.exec(statement)
    await session.commit()


async def get_knowledge_base_embedding_list(
    session: AsyncSession,
    knowledge_base_type: KnowledgeBaseTypeEnum,
    embedding_json: str,
):
    query = select(KnowledgeBase).order_by(
        text("embedding <-> :embedding")  # pgvector similarity
    )

    if knowledge_base_type:
        query = query.where(KnowledgeBase.type == knowledge_base_type)

    result = await session.execute(query, {"embedding": embedding_json})
    return result.scalars().all()
