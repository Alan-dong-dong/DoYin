from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings


def configure_media_environment(tmp_path: Path, monkeypatch) -> None:
    storage_root = tmp_path / "storage"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite+pysqlite:///{(tmp_path / 'media-runtime.sqlite3').as_posix()}",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcdef")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(storage_root / "uploads"))
    monkeypatch.setenv("HLS_DIR", str(storage_root / "hls"))
    monkeypatch.setenv("COVERS_DIR", str(storage_root / "covers"))
    monkeypatch.setenv("AVATARS_DIR", str(storage_root / "avatars"))
    monkeypatch.setenv("FFMPEG_BINARY", "custom-ffmpeg")
    monkeypatch.setenv("HLS_PUBLIC_PATH", "/media/hls")
    monkeypatch.setenv("COVERS_PUBLIC_PATH", "/media/covers")
    get_settings.cache_clear()


def test_create_app_wires_media_runtime_and_serves_media_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configure_media_environment(tmp_path, monkeypatch)

    try:
        from app.main import create_app

        application = create_app()
        media_runtime = application.state.media_runtime

        assert media_runtime.ffmpeg_binary == "custom-ffmpeg"
        assert media_runtime.uploads_dir == (tmp_path / "storage" / "uploads").resolve()
        assert media_runtime.hls_public_path == "/media/hls"
        assert media_runtime.covers_public_path == "/media/covers"
        assert media_runtime.upload_dir_for("video-123") == media_runtime.uploads_dir / "video-123"
        assert media_runtime.hls_dir.exists()
        assert media_runtime.covers_dir.exists()
        assert media_runtime.build_hls_url("video-123/index.m3u8") == "/media/hls/video-123/index.m3u8"
        assert media_runtime.build_cover_url("video-123/cover.jpg") == "/media/covers/video-123/cover.jpg"

        hls_file = media_runtime.hls_dir_for("video-123") / "index.m3u8"
        hls_file.parent.mkdir(parents=True, exist_ok=True)
        hls_file.write_text("#EXTM3U\n", encoding="utf-8")

        cover_file = media_runtime.cover_dir_for("video-123") / "cover.jpg"
        cover_file.parent.mkdir(parents=True, exist_ok=True)
        cover_file.write_bytes(b"cover")

        with TestClient(application) as client:
            hls_response = client.get("/media/hls/video-123/index.m3u8")
            assert hls_response.status_code == 200
            assert hls_response.text.splitlines() == ["#EXTM3U"]

            cover_response = client.get("/media/covers/video-123/cover.jpg")
            assert cover_response.status_code == 200
            assert cover_response.content == b"cover"
    finally:
        get_settings.cache_clear()
