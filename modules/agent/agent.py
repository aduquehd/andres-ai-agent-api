import pydantic_core
from pydantic_ai import Agent, RunContext
from pydantic_ai.agent import InstrumentationCap

from config import settings
from modules.agent.services import get_agent_context
from modules.knowledge_base.models import KnowledgeBaseTypeEnum
from modules.knowledge_base.services import get_knowledge_base_embedding_list
from modules.utils.agent import Deps
from modules.utils.embeddings import embed_query


agent = Agent(
    settings.agent_model,
    deps_type=Deps,
    capabilities=[InstrumentationCap()],
)


@agent.system_prompt(dynamic=True)
async def system_prompt(context: RunContext[Deps]) -> str:
    session = context.deps.session
    return await get_agent_context(session)


@agent.tool
async def search_knowledge_base(
    context: RunContext[Deps],
    category: KnowledgeBaseTypeEnum,
    search_query: str,
) -> str:
    """Semantic search over Andrés's knowledge base.

    Call this whenever the user asks about a topic that may be stored in
    the knowledge base. Choose the `category` that best matches:

    - hobbies: free-time activities and personal interests
    - favorite_foods: cuisines, dishes, and food preferences
    - professional_experience: detailed work history at specific companies
      (roles, achievements, technologies used). Use this when the user asks
      about a specific company or role; the static system prompt already
      covers high-level career summary.

    `search_query` should be a short natural-language phrase describing the
    user's question (e.g. "music", "weekend activities", "JetBridge",
    "what I did at Anomali").

    Returns a JSON array of {title, content} objects, or the literal string
    "NO_DATA" if nothing relevant is found.
    """
    embedding = await embed_query(search_query)
    embedding_json = pydantic_core.to_json(embedding).decode()

    session = context.deps.session
    knowledge_base_list = await get_knowledge_base_embedding_list(
        session,
        category,
        embedding_json,
        limit=30,
    )

    if not knowledge_base_list:
        return "NO_DATA"

    results = [{"title": kb.title, "content": kb.content} for kb in knowledge_base_list]
    return pydantic_core.to_json(results).decode()
