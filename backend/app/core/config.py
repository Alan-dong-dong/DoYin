from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _normalize_public_path(value: str, default: str) -> str:
    candidate = value.strip() if value.strip() else default
    if not candidate.startswith("/"):
        candidate = f"/{candidate}"
    if candidate != "/":
        candidate = candidate.rstrip("/")
    return candidate


def _resolve_path(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (Path.cwd() / candidate).resolve()


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    app_host: str
    app_port: int
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    ffmpeg_binary: str
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str
    cors_origins: tuple[str, ...]
    storage_root: str
    uploads_dir: str
    hls_dir: str
    covers_dir: str
    avatars_dir: str
    hls_public_path: str
    covers_public_path: str

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        database = self.postgres_db
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"

    @property
    def resolved_storage_root(self) -> Path:
        return _resolve_path(self.storage_root)

    @property
    def resolved_uploads_dir(self) -> Path:
        return _resolve_path(self.uploads_dir)

    @property
    def resolved_hls_dir(self) -> Path:
        return _resolve_path(self.hls_dir)

    @property
    def resolved_covers_dir(self) -> Path:
        return _resolve_path(self.covers_dir)

    @property
    def resolved_avatars_dir(self) -> Path:
        return _resolve_path(self.avatars_dir)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "DoYin API"),
            app_env=os.getenv("APP_ENV", "development"),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=int(os.getenv("APP_PORT", "8000")),
            jwt_secret_key=os.getenv(
                "JWT_SECRET_KEY",
                "local-dev-jwt-secret-change-me-123456",
            ),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_access_token_expire_minutes=int(
                os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "120")
            ),
            ffmpeg_binary=os.getenv("FFMPEG_BINARY", "ffmpeg"),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_db=os.getenv("POSTGRES_DB", "doyin"),
            postgres_user=os.getenv("POSTGRES_USER", "doyin"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "doyin"),
            database_url=os.getenv("DATABASE_URL", ""),
            cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173")),
            storage_root=os.getenv("STORAGE_ROOT", "../storage"),
            uploads_dir=os.getenv("UPLOADS_DIR", "../storage/uploads"),
            hls_dir=os.getenv("HLS_DIR", "../storage/hls"),
            covers_dir=os.getenv("COVERS_DIR", "../storage/covers"),
            avatars_dir=os.getenv("AVATARS_DIR", "../storage/avatars"),
            hls_public_path=_normalize_public_path(
                os.getenv("HLS_PUBLIC_PATH", "/media/hls"),
                "/media/hls",
            ),
            covers_public_path=_normalize_public_path(
                os.getenv("COVERS_PUBLIC_PATH", "/media/covers"),
                "/media/covers",
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
