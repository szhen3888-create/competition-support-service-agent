"""OpenAI 兼容协议 Provider（DeepSeek / Qwen / 豆包等均可走此实现）。"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.llm.base import ChatRequest, ChatResponse, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        base_url: str,
        default_model: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> None:
        self.name = name
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = AsyncOpenAI(
            api_key=api_key or "missing-key",
            base_url=base_url,
            timeout=timeout,
        )

    def _resolve_params(self, request: ChatRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": request.model or self.default_model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": (
                request.temperature if request.temperature is not None else self.temperature
            ),
            "max_tokens": request.max_tokens or self.max_tokens,
        }
        if request.tools:
            params["tools"] = request.tools
        return params

    async def chat(self, request: ChatRequest) -> ChatResponse:
        params = self._resolve_params(request)
        resp = await self._client.chat.completions.create(**params, stream=False)
        choice = resp.choices[0]
        message = choice.message
        usage = None
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens or 0,
                "completion_tokens": resp.usage.completion_tokens or 0,
                "total_tokens": resp.usage.total_tokens or 0,
            }
        return ChatResponse(
            content=message.content or "",
            model=resp.model or params["model"],
            provider=self.name,
            usage=usage,
            raw={"finish_reason": choice.finish_reason},
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        params = self._resolve_params(request)
        stream = await self._client.chat.completions.create(**params, stream=True)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def health_check(self) -> dict[str, Any]:
        if not self._client.api_key or self._client.api_key == "missing-key":
            return {
                "provider": self.name,
                "ok": False,
                "detail": "未配置 API Key（请在 backend/.env 设置 LLM_API_KEY）",
            }
        try:
            # 轻量探测：拉模型列表（部分厂商可能不支持，失败不代表完全不可用）
            await self._client.models.list()
            return {"provider": self.name, "ok": True, "base_url": str(self._client.base_url)}
        except Exception as exc:  # noqa: BLE001
            return {
                "provider": self.name,
                "ok": False,
                "detail": f"连通性检查失败: {exc}",
                "base_url": str(self._client.base_url),
            }
