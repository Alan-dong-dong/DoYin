from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import create_engine_from_url


def test_create_app_initializes_video_tables(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "runtime.sqlite3"
    storage_root = tmp_path / "storage"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite+pysqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcdef")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(storage_root / "uploads"))
    monkeypatch.setenv("HLS_DIR", str(storage_root / "hls"))
    monkeypatch.setenv("COVERS_DIR", str(storage_root / "covers"))
    monkeypatch.setenv("AVATARS_DIR", str(storage_root / "avatars"))
    get_settings.cache_clear()

    try:
        from app.main import create_app

        application = create_app()
        with TestClient(application):
            inspector = inspect(application.state.db_engine)
            table_names = set(inspector.get_table_names())
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            video_columns = {column["name"] for column in inspector.get_columns("videos")}

        assert "users" in table_names
        assert "videos" in table_names
        assert "upload_jobs" in table_names
        assert "is_admin" in user_columns
        assert "visibility" in video_columns
    finally:
        get_settings.cache_clear()


def test_create_app_adds_admin_and_visibility_columns_to_legacy_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "legacy-runtime.sqlite3"
    storage_root = tmp_path / "storage"
    engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    display_name VARCHAR(100) NOT NULL,
                    avatar_url VARCHAR(512),
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE videos (
                    id INTEGER PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    title VARCHAR(120) NOT NULL,
                    caption TEXT,
                    original_filename VARCHAR(255) NOT NULL,
                    original_content_type VARCHAR(255),
                    original_file_size INTEGER NOT NULL,
                    original_storage_path VARCHAR(1024) NOT NULL,
                    hls_manifest_path VARCHAR(1024),
                    cover_image_path VARCHAR(1024),
                    published_at DATETIME,
                    view_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
    engine.dispose()

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite+pysqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcdef")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(storage_root / "uploads"))
    monkeypatch.setenv("HLS_DIR", str(storage_root / "hls"))
    monkeypatch.setenv("COVERS_DIR", str(storage_root / "covers"))
    monkeypatch.setenv("AVATARS_DIR", str(storage_root / "avatars"))
    get_settings.cache_clear()

    try:
        from app.main import create_app

        application = create_app()
        with TestClient(application):
            inspector = inspect(application.state.db_engine)
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            video_columns = {column["name"] for column in inspector.get_columns("videos")}

        assert "is_admin" in user_columns
        assert "visibility" in video_columns
    finally:
        get_settings.cache_clear()
