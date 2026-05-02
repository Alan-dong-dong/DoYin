from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class MediaRuntime:
    ffmpeg_binary: str
    storage_root: Path
    uploads_dir: Path
    hls_dir: Path
    covers_dir: Path
    hls_public_path: str
    covers_public_path: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "MediaRuntime":
        return cls(
            ffmpeg_binary=settings.ffmpeg_binary,
            storage_root=settings.resolved_storage_root,
            uploads_dir=settings.resolved_uploads_dir,
            hls_dir=settings.resolved_hls_dir,
            covers_dir=settings.resolved_covers_dir,
            hls_public_path=settings.hls_public_path,
            covers_public_path=settings.covers_public_path,
        )

    def ensure_directories(self) -> None:
        for directory in (
            self.storage_root,
            self.uploads_dir,
            self.hls_dir,
            self.covers_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def upload_dir_for(self, video_id: str) -> Path:
        return self.uploads_dir / video_id

    def hls_dir_for(self, video_id: str) -> Path:
        return self.hls_dir / video_id

    def cover_dir_for(self, video_id: str) -> Path:
        return self.covers_dir / video_id

    def build_hls_url(self, relative_path: str) -> str:
        normalized = relative_path.lstrip("/").replace("\\", "/")
        return self.hls_public_path if not normalized else f"{self.hls_public_path}/{normalized}"

    def build_cover_url(self, relative_path: str) -> str:
        normalized = relative_path.lstrip("/").replace("\\", "/")
        return self.covers_public_path if not normalized else f"{self.covers_public_path}/{normalized}"


def init_media_runtime(application: FastAPI, settings: Settings) -> MediaRuntime:
    runtime = MediaRuntime.from_settings(settings)
    runtime.ensure_directories()
    application.state.media_runtime = runtime
    application.mount(
        runtime.hls_public_path,
        StaticFiles(directory=runtime.hls_dir),
        name="media-hls",
    )
    application.mount(
        runtime.covers_public_path,
        StaticFiles(directory=runtime.covers_dir),
        name="media-covers",
    )
    return runtime


def get_media_runtime(request: Request) -> MediaRuntime:
    return request.app.state.media_runtime
