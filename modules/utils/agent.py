from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from openai import AsyncOpenAI
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict


@dataclass
class Deps:
    openai: AsyncOpenAI
    session: AsyncSession | None = None


class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal["user", "model"]
    timestamp: str
    content: str


def to_chat_message(m: ModelMessage) -> ChatMessage | dict | None:
    if isinstance(m, ModelRequest):
        for part in m.parts:
            if isinstance(part, UserPromptPart):
                if not isinstance(part.content, str):
                    raise TypeError(f"Expected string content, got {type(part.content)}")
                return {
                    "role": "user",
                    "timestamp": part.timestamp.isoformat(),
                    "content": part.content,
                }
    elif isinstance(m, ModelResponse):
        for part in m.parts:
            if isinstance(part, TextPart):
                return {
                    "role": "model",
                    "timestamp": m.timestamp.isoformat(),
                    "content": part.content,
                }
    elif isinstance(m, AgentRunResult):
        return {
            "role": "model",
            "timestamp": datetime.now().isoformat(),
            "content": m.output,
        }
    else:
        return None
