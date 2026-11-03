"""LLM 配置查询与运行时切换（便于后台对接不同 API）。"""

import os

from fastapi import APIRouter

from app.api.schemas import LLMConfigUpdate, LLMRuntimeConfig
from app.core.config import get_settings
from app.llm import get_llm_provider, reset_llm_provider
from app.llm.factory import PROVIDER_DEFAULTS

router = APIRouter(prefix="/llm", tags=["llm"])


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def _current_config() -> LLMRuntimeConfig:
    settings = get_settings()
    return LLMRuntimeConfig(
        provider=settings.llm_provider,
        base_url=settings.resolved_base_url(),
        model=settings.llm_model,
        fast_model=settings.llm_fast_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
        api_key_configured=bool(settings.llm_api_key),
        api_key_masked=_mask_key(settings.llm_api_key),
    )


@router.get("/config", response_model=LLMRuntimeConfig)
async def get_llm_config() -> LLMRuntimeConfig:
    return _current_config()


@router.get("/providers")
async def list_providers() -> dict:
    return {
        "providers": [
            {
                "id": key,
                "default_base_url": value["base_url"],
                "default_model": value["model"],
            }
            for key, value in PROVIDER_DEFAULTS.items()
        ],
        "current": get_settings().llm_provider,
    }


@router.put("/config", response_model=LLMRuntimeConfig)
async def update_llm_config(body: LLMConfigUpdate) -> LLMRuntimeConfig:
    """
    运行时热更新 LLM 配置。

    说明：通过写入进程环境变量并清空 Settings/Provider 缓存生效；
    持久化请同步修改 backend/.env。
    """
    mapping = {
        "provider": "LLM_PROVIDER",
        "api_key": "LLM_API_KEY",
        "base_url": "LLM_BASE_URL",
        "model": "LLM_MODEL",
        "fast_model": "LLM_FAST_MODEL",
        "temperature": "LLM_TEMPERATURE",
        "max_tokens": "LLM_MAX_TOKENS",
        "timeout": "LLM_TIMEOUT",
    }
    data = body.model_dump(exclude_none=True)
    for field, env_key in mapping.items():
        if field in data:
            os.environ[env_key] = str(data[field])

    # 切换厂商且未显式传 base_url 时，自动套用预置地址
    if "provider" in data and "base_url" not in data:
        defaults = PROVIDER_DEFAULTS.get(data["provider"])
        if defaults:
            os.environ["LLM_BASE_URL"] = defaults["base_url"]
            if "model" not in data:
                os.environ["LLM_MODEL"] = defaults["model"]

    reset_llm_provider()
    return _current_config()


@router.post("/test")
async def test_llm() -> dict:
    """向当前 Provider 发送一条短消息，验证 API 可用性。"""
    provider = get_llm_provider()
    from app.llm import ChatMessage, ChatRequest

    try:
        result = await provider.chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="user", content="请只回复：OK"),
                ],
                max_tokens=16,
                temperature=0,
            )
        )
        return {
            "ok": True,
            "provider": result.provider,
            "model": result.model,
            "reply": result.content,
            "usage": result.usage,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "provider": provider.name}
