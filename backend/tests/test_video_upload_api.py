from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.domains.users.models import User
from app.domains.users.service import set_user_admin_status
from app.domains.videos.models import UploadJob, UploadJobStatus, Video, VideoVisibility
from app.domains.videos.service import (
    CreateUploadJobInput,
    CreateVideoInput,
    create_upload_job,
    create_video,
)


@pytest.fixture
def upload_client(tmp_path: Path, monkeypatch) -> TestClient:
    storage_root = tmp_path / "storage"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite+pysqlite:///{(tmp_path / 'upload-api.sqlite3').as_posix()}",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-1234567890-abcdef")
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))
    monkeypatch.setenv("UPLOADS_DIR", str(storage_root / "uploads"))
    monkeypatch.setenv("HLS_DIR", str(storage_root / "hls"))
    monkeypatch.setenv("COVERS_DIR", str(storage_root / "covers"))
    monkeypatch.setenv("AVATARS_DIR", str(storage_root / "avatars"))
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as client:
        yield client

    get_settings.cache_clear()


def authenticate_demo_user(client: TestClient) -> str:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "creator@example.com",
            "username": "creator",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "creator@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def get_user_id_by_email(client: TestClient, email: str) -> int:
    session = client.app.state.db_session_factory()
    try:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id
    finally:
        session.close()


def grant_admin_access(client: TestClient, email: str) -> None:
    session = client.app.state.db_session_factory()
    try:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        set_user_admin_status(session, user, is_admin=True)
        session.commit()
    finally:
        session.close()


def authenticate_admin_user(client: TestClient) -> str:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "username": "admin",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    grant_admin_access(client, "admin@example.com")
    return login_response.json()["access_token"]


def seed_feed_video(
    client: TestClient,
    *,
    creator_id: int,
    title: str,
    published_at: datetime | None = None,
    view_count: int = 0,
    visibility: VideoVisibility = VideoVisibility.PUBLIC,
    ready: bool = True,
) -> int:
    session = client.app.state.db_session_factory()
    try:
        video = create_video(
            session,
            CreateVideoInput(
                creator_id=creator_id,
                title=title,
                caption=f"{title} caption",
                original_filename="clip.mp4",
                original_content_type="video/mp4",
                original_file_size=2048,
                original_storage_path=f"uploads/{title.lower().replace(' ', '-')}/source.mp4",
                visibility=visibility,
                published_at=published_at if ready else None,
                view_count=view_count,
            ),
        )
        if ready:
            video.hls_manifest_path = f"hls/{video.id}/index.m3u8"
            video.cover_image_path = f"covers/{video.id}/cover.jpg"
        session.commit()
        return video.id
    finally:
        session.close()


def seed_admin_video(
    client: TestClient,
    *,
    creator_id: int,
    title: str,
    upload_status: UploadJobStatus,
    visibility: VideoVisibility = VideoVisibility.PUBLIC,
    failure_message: str | None = None,
    published_at: datetime | None = None,
) -> int:
    session = client.app.state.db_session_factory()
    try:
        video = create_video(
            session,
            CreateVideoInput(
                creator_id=creator_id,
                title=title,
                caption=f"{title} caption",
                original_filename="clip.mp4",
                original_content_type="video/mp4",
                original_file_size=2048,
                original_storage_path=f"uploads/{title.lower().replace(' ', '-')}/source.mp4",
                visibility=visibility,
                published_at=published_at,
            ),
        )
        if published_at is not None:
            video.hls_manifest_path = f"hls/{video.id}/index.m3u8"
            video.cover_image_path = f"covers/{video.id}/cover.jpg"

        upload_job = create_upload_job(
            session,
            CreateUploadJobInput(video_id=video.id, status=upload_status),
        )
        upload_job.failure_message = failure_message
        session.commit()
        return video.id
    finally:
        session.close()


def test_create_video_upload_accepts_valid_video_and_persists_records(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.domains.videos.router.process_upload_job", lambda *args: None)
    access_token = authenticate_demo_user(upload_client)

    response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "My upload", "caption": "Hello world"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["video_id"] > 0
    assert payload["upload_job_id"] > 0

    session = upload_client.app.state.db_session_factory()
    try:
        video = session.scalar(select(Video).where(Video.id == payload["video_id"]))
        upload_job = session.scalar(
            select(UploadJob).where(UploadJob.id == payload["upload_job_id"])
        )
        assert video is not None
        assert video.title == "My upload"
        assert video.caption == "Hello world"
        assert video.original_storage_path == f"uploads/{video.id}/source.mp4"
        assert video.original_file_size == len(b"fake-video")
        assert video.visibility is VideoVisibility.PUBLIC

        assert upload_job is not None
        assert upload_job.video_id == video.id
        assert upload_job.status is UploadJobStatus.PENDING

        stored_file = upload_client.app.state.media_runtime.storage_root / video.original_storage_path
        assert stored_file.exists()
        assert stored_file.read_bytes() == b"fake-video"
    finally:
        session.close()


def test_create_video_upload_rejects_non_video_files(upload_client: TestClient) -> None:
    access_token = authenticate_demo_user(upload_client)

    response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Not a video"},
        files={"video_file": ("notes.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "A supported video file is required."

    session = upload_client.app.state.db_session_factory()
    try:
        assert session.scalar(select(Video)) is None
        assert session.scalar(select(UploadJob)) is None
    finally:
        session.close()


def test_create_video_upload_processes_job_in_background_and_updates_assets(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    def fake_run_ffmpeg_pipeline(media_runtime, source_path, video_id):
        hls_dir = media_runtime.hls_dir_for(str(video_id))
        cover_dir = media_runtime.cover_dir_for(str(video_id))
        hls_dir.mkdir(parents=True, exist_ok=True)
        cover_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = hls_dir / "index.m3u8"
        manifest_path.write_text("#EXTM3U\n", encoding="utf-8")
        cover_path = cover_dir / "cover.jpg"
        cover_path.write_bytes(b"cover")

        from app.domains.videos.processing import ProcessedVideoAssets

        return ProcessedVideoAssets(
            hls_manifest_path=manifest_path.relative_to(media_runtime.storage_root).as_posix(),
            cover_image_path=cover_path.relative_to(media_runtime.storage_root).as_posix(),
        )

    monkeypatch.setattr(
        "app.domains.videos.processing.run_ffmpeg_pipeline",
        fake_run_ffmpeg_pipeline,
    )
    access_token = authenticate_demo_user(upload_client)

    response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Background job"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending"

    session = upload_client.app.state.db_session_factory()
    try:
        video = session.scalar(select(Video).where(Video.id == payload["video_id"]))
        upload_job = session.scalar(
            select(UploadJob).where(UploadJob.id == payload["upload_job_id"])
        )
        assert video is not None
        assert upload_job is not None
        assert upload_job.status is UploadJobStatus.READY
        assert upload_job.started_at is not None
        assert upload_job.finished_at is not None
        assert video.hls_manifest_path == f"hls/{video.id}/index.m3u8"
        assert video.cover_image_path == f"covers/{video.id}/cover.jpg"

        manifest_path = upload_client.app.state.media_runtime.storage_root / video.hls_manifest_path
        cover_path = upload_client.app.state.media_runtime.storage_root / video.cover_image_path
        assert manifest_path.exists()
        assert cover_path.exists()
    finally:
        session.close()


def test_read_upload_job_status_returns_pending_state_for_owner(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.domains.videos.router.process_upload_job", lambda *args: None)
    access_token = authenticate_demo_user(upload_client)

    create_response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Pending upload"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )
    upload_job_id = create_response.json()["upload_job_id"]

    response = upload_client.get(
        f"/api/videos/uploads/{upload_job_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["hls_manifest_url"] is None
    assert payload["cover_image_url"] is None
    assert payload["failure_message"] is None


def test_read_upload_job_status_returns_ready_assets_for_owner(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    def fake_run_ffmpeg_pipeline(media_runtime, source_path, video_id):
        hls_dir = media_runtime.hls_dir_for(str(video_id))
        cover_dir = media_runtime.cover_dir_for(str(video_id))
        hls_dir.mkdir(parents=True, exist_ok=True)
        cover_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = hls_dir / "index.m3u8"
        manifest_path.write_text("#EXTM3U\n", encoding="utf-8")
        cover_path = cover_dir / "cover.jpg"
        cover_path.write_bytes(b"cover")

        from app.domains.videos.processing import ProcessedVideoAssets

        return ProcessedVideoAssets(
            hls_manifest_path=manifest_path.relative_to(media_runtime.storage_root).as_posix(),
            cover_image_path=cover_path.relative_to(media_runtime.storage_root).as_posix(),
        )

    monkeypatch.setattr(
        "app.domains.videos.processing.run_ffmpeg_pipeline",
        fake_run_ffmpeg_pipeline,
    )
    access_token = authenticate_demo_user(upload_client)

    create_response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Ready upload"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )
    upload_job_id = create_response.json()["upload_job_id"]
    video_id = create_response.json()["video_id"]

    response = upload_client.get(
        f"/api/videos/uploads/{upload_job_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["hls_manifest_url"] == f"/media/hls/{video_id}/index.m3u8"
    assert payload["cover_image_url"] == f"/media/covers/{video_id}/cover.jpg"


def test_read_upload_job_status_rejects_non_owner(upload_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.domains.videos.router.process_upload_job", lambda *args: None)
    owner_token = authenticate_demo_user(upload_client)

    create_response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {owner_token}"},
        data={"title": "Owner upload"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )
    upload_job_id = create_response.json()["upload_job_id"]

    register_response = upload_client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "username": "viewer",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    login_response = upload_client.post(
        "/api/auth/login",
        json={"email": "viewer@example.com", "password": "secret123"},
    )
    viewer_token = login_response.json()["access_token"]

    response = upload_client.get(
        f"/api/videos/uploads/{upload_job_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Upload job was not found."


def test_create_video_upload_marks_job_failed_when_processing_fails(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    def failing_pipeline(*_args, **_kwargs):
        raise RuntimeError("ffmpeg failed to transcode the uploaded file")

    monkeypatch.setattr(
        "app.domains.videos.processing.run_ffmpeg_pipeline",
        failing_pipeline,
    )
    access_token = authenticate_demo_user(upload_client)

    create_response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Broken upload"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )

    assert create_response.status_code == 202
    upload_job_id = create_response.json()["upload_job_id"]

    response = upload_client.get(
        f"/api/videos/uploads/{upload_job_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["failure_message"] == "ffmpeg failed to transcode the uploaded file"
    assert payload["hls_manifest_url"] is None
    assert payload["cover_image_url"] is None


def test_read_video_feed_returns_paginated_ready_items_in_stable_order(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)
    creator_id = get_user_id_by_email(upload_client, "creator@example.com")
    now = datetime.now(UTC)

    pending_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Pending video",
        ready=False,
    )
    older_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Older video",
        published_at=now - timedelta(minutes=30),
    )
    freshest_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Freshest video",
        published_at=now,
    )
    hotter_recent_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Hotter recent video",
        published_at=now - timedelta(minutes=4),
        view_count=2,
    )

    first_response = upload_client.get(
        "/api/videos/feed?page=1&page_size=2",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    repeat_response = upload_client.get(
        "/api/videos/feed?page=1&page_size=2",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    second_response = upload_client.get(
        "/api/videos/feed?page=2&page_size=2",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert first_response.status_code == 200
    assert repeat_response.status_code == 200
    assert second_response.status_code == 200

    first_payload = first_response.json()
    repeat_payload = repeat_response.json()
    second_payload = second_response.json()

    assert [item["id"] for item in first_payload["items"]] == [
        hotter_recent_video_id,
        freshest_video_id,
    ]
    assert [item["id"] for item in repeat_payload["items"]] == [
        hotter_recent_video_id,
        freshest_video_id,
    ]
    assert [item["id"] for item in second_payload["items"]] == [older_video_id]
    assert pending_video_id not in [item["id"] for item in first_payload["items"]]
    assert first_payload["has_more"] is True
    assert second_payload["has_more"] is False
    assert first_payload["page"] == 1
    assert first_payload["page_size"] == 2
    assert first_payload["items"][0]["creator"]["id"] == creator_id
    assert first_payload["items"][0]["creator"]["username"] == "creator"
    assert first_payload["items"][0]["hls_manifest_url"] == (
        f"/media/hls/{hotter_recent_video_id}/index.m3u8"
    )
    assert first_payload["items"][0]["cover_image_url"] == (
        f"/media/covers/{hotter_recent_video_id}/cover.jpg"
    )


def test_read_video_feed_returns_empty_page_when_no_ready_videos(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)

    response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 5,
        "has_more": False,
    }


def test_read_video_feed_skips_candidates_with_invalid_asset_references(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)
    creator_id = get_user_id_by_email(upload_client, "creator@example.com")
    now = datetime.now(UTC)

    seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Broken paths",
        published_at=now,
    )
    session = upload_client.app.state.db_session_factory()
    try:
        broken_video = session.scalar(select(Video).where(Video.title == "Broken paths"))
        assert broken_video is not None
        broken_video.hls_manifest_path = "broken/index.m3u8"
        session.commit()
    finally:
        session.close()

    valid_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Healthy video",
        published_at=now - timedelta(minutes=1),
    )

    response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [valid_video_id]


def test_read_video_feed_excludes_hidden_ready_videos(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)
    creator_id = get_user_id_by_email(upload_client, "creator@example.com")
    now = datetime.now(UTC)

    hidden_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Hidden ready video",
        published_at=now,
        visibility=VideoVisibility.HIDDEN,
    )
    public_video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Public ready video",
        published_at=now - timedelta(minutes=1),
    )

    response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert hidden_video_id not in [item["id"] for item in payload["items"]]
    assert [item["id"] for item in payload["items"]] == [public_video_id]


def test_record_video_playback_increments_hotness_for_ready_video(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)
    creator_id = get_user_id_by_email(upload_client, "creator@example.com")
    video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Playback ready",
        published_at=datetime.now(UTC),
    )

    response = upload_client.post(
        f"/api/videos/{video_id}/playbacks",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "view_count": 1,
    }

    session = upload_client.app.state.db_session_factory()
    try:
        video = session.scalar(select(Video).where(Video.id == video_id))
        assert video is not None
        assert video.view_count == 1
    finally:
        session.close()


def test_record_video_playback_rejects_non_ready_video(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)
    creator_id = get_user_id_by_email(upload_client, "creator@example.com")
    video_id = seed_feed_video(
        upload_client,
        creator_id=creator_id,
        title="Playback pending",
        ready=False,
    )

    response = upload_client.post(
        f"/api/videos/{video_id}/playbacks",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Video is not ready for playback."

    session = upload_client.app.state.db_session_factory()
    try:
        video = session.scalar(select(Video).where(Video.id == video_id))
        assert video is not None
        assert video.view_count == 0
    finally:
        session.close()


def test_upload_to_feed_to_playback_smoke_flow(
    upload_client: TestClient,
    monkeypatch,
) -> None:
    def fake_run_ffmpeg_pipeline(media_runtime, source_path, video_id):
        hls_dir = media_runtime.hls_dir_for(str(video_id))
        cover_dir = media_runtime.cover_dir_for(str(video_id))
        hls_dir.mkdir(parents=True, exist_ok=True)
        cover_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = hls_dir / "index.m3u8"
        manifest_path.write_text("#EXTM3U\n", encoding="utf-8")
        cover_path = cover_dir / "cover.jpg"
        cover_path.write_bytes(b"cover")

        from app.domains.videos.processing import ProcessedVideoAssets

        return ProcessedVideoAssets(
            hls_manifest_path=manifest_path.relative_to(media_runtime.storage_root).as_posix(),
            cover_image_path=cover_path.relative_to(media_runtime.storage_root).as_posix(),
        )

    monkeypatch.setattr(
        "app.domains.videos.processing.run_ffmpeg_pipeline",
        fake_run_ffmpeg_pipeline,
    )
    access_token = authenticate_demo_user(upload_client)

    upload_response = upload_client.post(
        "/api/videos/uploads",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"title": "Feed smoke video"},
        files={"video_file": ("clip.mp4", b"fake-video", "video/mp4")},
    )

    assert upload_response.status_code == 202
    video_id = upload_response.json()["video_id"]

    feed_response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert feed_response.status_code == 200
    feed_items = feed_response.json()["items"]
    assert len(feed_items) == 1
    assert feed_items[0]["id"] == video_id
    assert feed_items[0]["hls_manifest_url"] == f"/media/hls/{video_id}/index.m3u8"

    playback_response = upload_client.post(
        f"/api/videos/{video_id}/playbacks",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert playback_response.status_code == 200
    assert playback_response.json() == {
        "video_id": video_id,
        "view_count": 1,
    }


def test_admin_video_inventory_rejects_non_admin_users(
    upload_client: TestClient,
) -> None:
    access_token = authenticate_demo_user(upload_client)

    response = upload_client.get(
        "/api/videos/admin",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required."


def test_admin_video_inventory_returns_filtered_results_with_failure_reason(
    upload_client: TestClient,
) -> None:
    admin_token = authenticate_admin_user(upload_client)
    admin_id = get_user_id_by_email(upload_client, "admin@example.com")
    now = datetime.now(UTC)

    matching_video_id = seed_admin_video(
        upload_client,
        creator_id=admin_id,
        title="Broken admin upload",
        upload_status=UploadJobStatus.FAILED,
        visibility=VideoVisibility.HIDDEN,
        failure_message="ffmpeg exited with code 1",
    )
    seed_admin_video(
        upload_client,
        creator_id=admin_id,
        title="Healthy public upload",
        upload_status=UploadJobStatus.READY,
        visibility=VideoVisibility.PUBLIC,
        published_at=now,
    )

    response = upload_client.get(
        "/api/videos/admin?page=1&page_size=10&status=failed&visibility=hidden&q=broken",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 1
    assert payload["has_more"] is False
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert [item["id"] for item in payload["items"]] == [matching_video_id]
    assert payload["items"][0]["creator"]["email"] == "admin@example.com"
    assert payload["items"][0]["latest_upload_status"] == "failed"
    assert payload["items"][0]["failure_message"] == "ffmpeg exited with code 1"
    assert payload["items"][0]["visibility"] == "hidden"


def test_admin_can_hide_and_restore_video_visibility(
    upload_client: TestClient,
) -> None:
    admin_token = authenticate_admin_user(upload_client)
    admin_id = get_user_id_by_email(upload_client, "admin@example.com")
    now = datetime.now(UTC)

    video_id = seed_admin_video(
        upload_client,
        creator_id=admin_id,
        title="Moderated ready video",
        upload_status=UploadJobStatus.READY,
        visibility=VideoVisibility.PUBLIC,
        published_at=now,
    )

    hide_response = upload_client.patch(
        f"/api/videos/admin/{video_id}/visibility",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "hidden"},
    )

    assert hide_response.status_code == 200
    assert hide_response.json() == {
        "video_id": video_id,
        "visibility": "hidden",
    }

    hidden_feed_response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert hidden_feed_response.status_code == 200
    assert video_id not in [item["id"] for item in hidden_feed_response.json()["items"]]

    restore_response = upload_client.patch(
        f"/api/videos/admin/{video_id}/visibility",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"visibility": "public"},
    )

    assert restore_response.status_code == 200
    assert restore_response.json() == {
        "video_id": video_id,
        "visibility": "public",
    }

    restored_feed_response = upload_client.get(
        "/api/videos/feed",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert restored_feed_response.status_code == 200
    assert [item["id"] for item in restored_feed_response.json()["items"]] == [video_id]


def test_admin_visibility_update_rejects_unauthenticated_and_non_admin_callers(
    upload_client: TestClient,
) -> None:
    admin_token = authenticate_admin_user(upload_client)
    admin_id = get_user_id_by_email(upload_client, "admin@example.com")
    video_id = seed_admin_video(
        upload_client,
        creator_id=admin_id,
        title="Protected moderation target",
        upload_status=UploadJobStatus.READY,
        published_at=datetime.now(UTC),
    )
    viewer_token = authenticate_demo_user(upload_client)

    unauthenticated_response = upload_client.patch(
        f"/api/videos/admin/{video_id}/visibility",
        json={"visibility": "hidden"},
    )
    non_admin_response = upload_client.patch(
        f"/api/videos/admin/{video_id}/visibility",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"visibility": "hidden"},
    )

    assert unauthenticated_response.status_code == 401
    assert non_admin_response.status_code == 403
