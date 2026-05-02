from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.media import init_media_runtime
from app.db.runtime import dispose_database, init_database


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    init_database(application, settings)
    try:
        yield
    finally:
        dispose_database(application)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    init_media_runtime(application, settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
