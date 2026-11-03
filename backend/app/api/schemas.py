"""API 请求/响应模型。"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class ChatBody(BaseModel):
    messages: list[ChatMessageIn] = Field(..., min_length=1)
    stream: bool = False
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    context: dict[str, Any] | None = None


class ChatResult(BaseModel):
    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None


class LLMRuntimeConfig(BaseModel):
    """对外展示的当前 LLM 运行配置（不含完整 Key）。"""

    provider: str
    base_url: str
    model: str
    fast_model: str
    temperature: float
    max_tokens: int
    timeout: int
    api_key_configured: bool
    api_key_masked: str


class LLMConfigUpdate(BaseModel):
    """运行时更新 LLM 配置（写入进程环境，重启后以 .env 为准）。"""

    provider: Literal["deepseek", "openai_compatible", "qwen", "doubao"] | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    fast_model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    timeout: int | None = Field(default=None, ge=5)


class HealthResult(BaseModel):
    status: str
    app: str
    version: str
    llm: dict[str, Any]
