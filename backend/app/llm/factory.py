"""根据配置创建 LLM Provider。"""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.providers.openai_compatible import OpenAICompatibleProvider


# 预置厂商默认模型（可被环境变量覆盖）
PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-pro-32k",
    },
    "openai_compatible": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
}


def create_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider_name = settings.llm_provider
    defaults = PROVIDER_DEFAULTS.get(provider_name, PROVIDER_DEFAULTS["openai_compatible"])

    base_url = settings.resolved_base_url() or defaults["base_url"]
    model = settings.llm_model or defaults["model"]

    return OpenAICompatibleProvider(
        name=provider_name,
        api_key=settings.llm_api_key,
        base_url=base_url,
        default_model=model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    return create_provider()


def reset_llm_provider() -> None:
    """配置热更新后清空缓存。"""
    get_llm_provider.cache_clear()
    get_settings.cache_clear()
