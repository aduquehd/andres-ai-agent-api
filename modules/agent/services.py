from pydantic_ai.models.anthropic import AnthropicModelSettings
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from config import settings
from modules.agent.models import AgentContext, AgentModelConfig


AGENT_MODEL_CONFIG_ID = 1


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


async def get_agent_model_config(session: AsyncSession) -> AgentModelConfig:
    """Return the config saved in the admin, or an unsaved default from settings."""
    config = await session.get(AgentModelConfig, AGENT_MODEL_CONFIG_ID)
    return config or AgentModelConfig(model=settings.agent_model)


def build_model_settings(config: AgentModelConfig) -> AnthropicModelSettings:
    """Translate a config into Pydantic AI model settings, skipping unset fields.

    Unset fields fall back to the agent's own settings (``DEFAULT_MAX_TOKENS``).
    ``anthropic_effort`` is sent as-is to Anthropic models and ignored by other providers.
    """
    model_settings = AnthropicModelSettings()
    if config.effort:
        model_settings["anthropic_effort"] = config.effort
    if config.max_tokens is not None:
        model_settings["max_tokens"] = config.max_tokens
    if config.temperature is not None:
        model_settings["temperature"] = config.temperature
    return model_settings
