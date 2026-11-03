from fastapi import APIRouter

from app.api.routes import auth, chat, competitions, exports, health, knowledge, llm_config, stats, team, workspace


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(chat.router)
    router.include_router(llm_config.router)
    router.include_router(knowledge.router)
    router.include_router(competitions.router)
    router.include_router(stats.router)
    router.include_router(workspace.router)
    router.include_router(exports.router)
    router.include_router(team.router)
    return router
