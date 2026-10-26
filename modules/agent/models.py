from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP, Text
from sqlmodel import Field, SQLModel


class AgentContext(SQLModel, table=True):
    __tablename__ = "agent_context"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    status: bool = Field(False)
    agent_prompt: str | None = Field(None, sa_type=Text)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=TIMESTAMP(timezone=True),
    )


class AgentModelConfig(SQLModel, table=True):
    """Model and request settings for the chat agent, editable from the admin.

    A single row (see ``AGENT_MODEL_CONFIG_ID``). With no row saved, the agent
    uses ``settings.agent_model`` and its own default settings (``DEFAULT_MAX_TOKENS``).
    """

    __tablename__ = "agent_model_config"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    model: str
    effort: str | None = Field(default=None)
    max_tokens: int | None = Field(default=None)
    temperature: float | None = Field(default=None)

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=TIMESTAMP(timezone=True),
    )
