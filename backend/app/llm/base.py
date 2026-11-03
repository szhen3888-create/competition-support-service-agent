"""LLM Provider 抽象接口。"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="system | user | assistant | tool")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    tools: list[dict[str, Any]] | None = None


class ChatChoice(BaseModel):
    role: str = "assistant"
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None
    raw: dict[str, Any] | None = None


class LLMProvider(ABC):
    """统一聊天接口，便于切换 DeepSeek / Qwen / 豆包等。"""

    name: str = "base"

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话。"""

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """流式对话，逐段产出文本。"""

    async def health_check(self) -> dict[str, Any]:
        """探测 Provider 是否可用（不强制实现完整连通）。"""
        return {"provider": self.name, "ok": True}
