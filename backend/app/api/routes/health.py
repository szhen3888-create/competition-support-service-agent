from fastapi import APIRouter

from app import __version__
from app.api.schemas import HealthResult
from app.core.config import get_settings
from app.llm import get_llm_provider

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResult)
async def health() -> HealthResult:
    settings = get_settings()
    provider = get_llm_provider()
    llm_status = await provider.health_check()
    overall = "ok" if llm_status.get("ok") else "degraded"
    return HealthResult(
        status=overall,
        app=settings.app_name,
        version=__version__,
        llm=llm_status,
    )
