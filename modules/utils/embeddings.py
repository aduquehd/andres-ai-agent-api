"""OpenAI embeddings helper.

Both index-time (admin save) and query-time (agent tool) must go through
this module so they share the same model and stay in the same vector space.
"""

import logfire
from openai import AsyncOpenAI

from config import settings


_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
        logfire.instrument_openai(_client)
    return _client


async def _embed_one(text: str) -> list[float]:
    response = await _get_client().embeddings.create(
        input=text,
        model=settings.embedding_model,
    )
    if len(response.data) != 1:
        raise ValueError(f"Expected 1 embedding, got {len(response.data)}")
    return response.data[0].embedding


async def embed_query(text: str) -> list[float]:
    """Embed a search query. Use this on the read path."""
    return await _embed_one(text)


async def embed_document(text: str) -> list[float]:
    """Embed a knowledge-base entry for storage. Use this on the write path."""
    return await _embed_one(text)
