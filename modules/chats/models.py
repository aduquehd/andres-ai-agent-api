from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import TIMESTAMP, Enum as SqlEnum
from sqlmodel import Column, Field, Relationship, SQLModel

from modules.users.models import User


class MessageDirectionEnum(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"


class AgentMessage(SQLModel, table=True):
    __tablename__ = "agent_messages"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    message_list: str
    user_id: int = Field(default=None, foreign_key="users.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
    )

    # Relationship back to user
    user: User = Relationship(back_populates="agent_messages")


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    message: str
    direction: MessageDirectionEnum = Field(
        sa_column=Column(SqlEnum(MessageDirectionEnum), nullable=False)
    )
    user_id: int = Field(default=None, foreign_key="users.id")
    ip_address: str | None = Field(default=None, max_length=45)  # IPv6 can be up to 45 chars
    user_agent: str | None = Field(default=None, max_length=500)  # Browser/device info
    response_time_ms: int | None = Field(default=None)  # Response time in milliseconds
    country: str | None = Field(default=None, max_length=2)  # ISO country code
    region: str | None = Field(default=None, max_length=100)  # State/region
    city: str | None = Field(default=None, max_length=100)  # City name

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
    )

    # Relationship back to user
    user: User = Relationship(back_populates="messages")
