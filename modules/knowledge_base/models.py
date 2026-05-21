from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, Enum as SqlEnum
from sqlmodel import Column, Field, SQLModel


class KnowledgeBaseTypeEnum(str, Enum):
    hobbies = "hobbies"
    foods = "foods"


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_base"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    type: KnowledgeBaseTypeEnum = Field(
        sa_column=Column(SqlEnum(KnowledgeBaseTypeEnum), nullable=False)
    )
    title: str
    content: str
    embedding: list[float] = Field(sa_column=Column(Vector(1536), nullable=True))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
    )
