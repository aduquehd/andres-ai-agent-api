import json
from typing import Any

import logfire
import pydantic_core
from pydantic_ai import Agent, RunContext

from modules.agent.services import get_agent_context
from modules.knowledge_base.models import KnowledgeBaseTypeEnum
from modules.knowledge_base.services import get_knowledge_base_embedding_list
from modules.utils.agent import Deps


logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_asyncpg()

agent = Agent(
    "openai:gpt-4o",
    deps_type=Deps,
    instrument=True,
)


@agent.system_prompt(dynamic=True)
async def system_prompt(context: RunContext[Deps]) -> str:
    session = context.deps.session
    return await get_agent_context(session)


async def _get_query_embedding(openai_client: Any, query: str) -> list[float]:
    embedding = await openai_client.embeddings.create(
        input=query,
        model="text-embedding-3-small",
    )
    if len(embedding.data) != 1:
        raise ValueError(f"Expected 1 embedding, got {len(embedding.data)}, query: {query!r}")
    return embedding.data[0].embedding


@agent.tool
async def agent_hobbies(context: RunContext[Deps], search_query: str) -> str:
    embedding = await _get_query_embedding(context.deps.openai, search_query)
    embedding_json = pydantic_core.to_json(embedding).decode()

    session = context.deps.session
    knowledge_base_list = await get_knowledge_base_embedding_list(
        session, KnowledgeBaseTypeEnum.hobbies, embedding_json
    )

    if not knowledge_base_list:
        return "NO_DATA"

    results = [{"title": kb.title, "content": kb.content} for kb in knowledge_base_list]
    return json.dumps(results)
