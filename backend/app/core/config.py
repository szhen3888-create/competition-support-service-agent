"""应用配置：从环境变量加载，支持 DeepSeek 及任意 OpenAI 兼容 API。"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "竞赛辅助服务智能体"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM Provider
    llm_provider: Literal["deepseek", "openai_compatible", "qwen", "doubao"] = "deepseek"
    llm_api_key: str = Field(default="", description="LLM API Key")
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_fast_model: str = "deepseek-chat"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_timeout: int = 60

    # 数据（骨架阶段可选）
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/competition_agent"
    chroma_persist_dir: str = "./data/chroma"
    knowledge_dir: str = "./data/knowledge"
    rag_top_k: int = 5
    rag_max_rewrite: int = 2

    # 认证（轻量 JWT）
    jwt_secret: str = Field(default="competition-agent-dev-secret-change-me", description="JWT 签名密钥")
    jwt_expire_hours: int = 72

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_base_url(self) -> str:
        """按 provider 补全默认 Base URL（用户显式配置优先）。"""
        defaults = {
            "deepseek": "https://api.deepseek.com",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "doubao": "https://ark.cn-beijing.volces.com/api/v3",
            "openai_compatible": self.llm_base_url,
        }
        # 若用户已改过 base_url（非 deepseek 默认），以用户为准
        if self.llm_provider == "deepseek" and self.llm_base_url:
            return self.llm_base_url.rstrip("/")
        if self.llm_provider == "openai_compatible":
            return self.llm_base_url.rstrip("/")
        # qwen / doubao：若仍是 deepseek 默认地址，则切换到对应默认
        if self.llm_base_url.rstrip("/") == "https://api.deepseek.com":
            return defaults.get(self.llm_provider, self.llm_base_url).rstrip("/")
        return self.llm_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
