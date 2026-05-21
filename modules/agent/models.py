from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, Text
from sqlmodel import Field, SQLModel


class AgentContext(SQLModel, table=True):
    __tablename__ = "agent_context"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    status: bool = Field(False)
    agent_prompt: str | None = Field(None, sa_type=Text)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
    )
