from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from fastapi import FastAPI, Request
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base, load_model_metadata
from app.db.session import create_engine_from_url, create_session_factory


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    engine: Engine
    session_factory: sessionmaker


def _ensure_additive_schema_updates(engine: Engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        if inspector.has_table("users"):
            existing_user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "is_admin" not in existing_user_columns:
                default_literal = "0" if engine.dialect.name == "sqlite" else "FALSE"
                connection.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT {default_literal}"
                    )
                )

        if inspector.has_table("videos"):
            existing_video_columns = {column["name"] for column in inspector.get_columns("videos")}
            if "visibility" not in existing_video_columns:
                connection.execute(
                    text(
                        "ALTER TABLE videos ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'public'"
                    )
                )


def init_database(app: FastAPI, settings: Settings) -> DatabaseRuntime:
    engine = create_engine_from_url(settings.resolved_database_url)
    load_model_metadata()
    Base.metadata.create_all(bind=engine)
    _ensure_additive_schema_updates(engine)
    runtime = DatabaseRuntime(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    app.state.db_engine = runtime.engine
    app.state.db_session_factory = runtime.session_factory
    return runtime


def dispose_database(app: FastAPI) -> None:
    engine: Engine | None = getattr(app.state, "db_engine", None)
    if engine is not None:
        engine.dispose()


def get_session_factory(request: Request) -> sessionmaker:
    return request.app.state.db_session_factory


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = get_session_factory(request)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
