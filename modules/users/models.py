from datetime import datetime, timezone
from typing import ForwardRef, List, Optional

from sqlalchemy import TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel


# Forward reference to avoid circular dependency
MessagesRef = ForwardRef("Message")
AgentMessagesRef = ForwardRef("AgentMessage")


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    browser_id: str = Field(index=True)

    # Creation metadata fields (similar to Message model)
    ip_address: str | None = Field(default=None, max_length=45)  # IPv6 can be up to 45 chars
    user_agent: str | None = Field(default=None, max_length=500)  # Browser/device info
    country: str | None = Field(default=None, max_length=2)  # ISO country code
    region: str | None = Field(default=None, max_length=100)  # State/region
    city: str | None = Field(default=None, max_length=100)  # City name

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
    )

    # Relationships
    messages: List["Message"] = Relationship(back_populates="user")
    agent_messages: List["AgentMessage"] = Relationship(back_populates="user")
