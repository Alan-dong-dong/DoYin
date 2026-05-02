from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.health.router import router as health_router
from app.domains.videos.router import router as videos_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(videos_router)
