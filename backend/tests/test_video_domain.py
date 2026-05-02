from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.media import MediaRuntime
from app.db.base import Base
from app.db.session import create_engine_from_url, create_session_factory
from app.domains.users.models import User
from app.domains.videos.models import UploadJobStatus, VideoVisibility
from app.domains.videos.processing import ProcessedVideoAssets, process_upload_job
from app.domains.videos.schemas import UploadJobRecord, VideoRecord
from app.domains.videos.service import (
    CreateUploadJobInput,
    CreateVideoInput,
    create_upload_job,
    create_video,
    get_upload_job_by_id,
    get_video_by_id,
    is_video_publicly_visible,
    is_video_ready_for_feed,
    list_feed_videos,
)


def create_test_session_factory(tmp_path: Path):
    engine = create_engine_from_url(
        f"sqlite+pysqlite:///{(tmp_path / 'video-domain.sqlite3').as_posix()}"
    )
    Base.metadata.create_all(bind=engine)
    return create_session_factory(engine)


def create_test_session(tmp_path: Path) -> Session:
    return create_test_session_factory(tmp_path)()


def create_creator(session: Session, email: str = "creator@example.com") -> User:
    creator = User(
        email=email,
        username=email.split("@", maxsplit=1)[0],
        display_name=email.split("@", maxsplit=1)[0],
        password_hash="hashed-password",
    )
    session.add(creator)
    session.flush()
    return creator


def create_video_record(
    session: Session,
    creator_id: int,
    *,
    title: str,
    original_storage_path: str,
    visibility: VideoVisibility = VideoVisibility.PUBLIC,
    published_at: datetime | None = None,
    view_count: int = 0,
    hls_manifest_path: str | None = None,
    cover_image_path: str | None = None,
) -> None:
    video = create_video(
        session,
        CreateVideoInput(
            creator_id=creator_id,
            title=title,
            caption="Minimal publish metadata",
            original_filename="clip.mp4",
            original_content_type="video/mp4",
            original_file_size=2048,
            original_storage_path=original_storage_path,
            visibility=visibility,
            published_at=published_at,
            view_count=view_count,
        ),
    )
    video.hls_manifest_path = hls_manifest_path
    video.cover_image_path = cover_image_path
    session.flush()


def test_video_domain_persists_video_metadata_and_upload_job_lifecycle(
    tmp_path: Path,
) -> None:
    session = create_test_session(tmp_path)

    try:
        creator = User(
            email="creator@example.com",
            username="creator",
            display_name="creator",
            password_hash="hashed-password",
        )
        session.add(creator)
        session.flush()

        video = create_video(
            session,
            CreateVideoInput(
                creator_id=creator.id,
                title="My first upload",
                caption="Minimal publish metadata",
                original_filename="clip.mp4",
                original_content_type="video/mp4",
                original_file_size=2048,
                original_storage_path="uploads/1/clip.mp4",
            ),
        )
        upload_job = create_upload_job(
            session,
            CreateUploadJobInput(video_id=video.id),
        )
        session.commit()

        persisted_video = get_video_by_id(session, video.id)
        persisted_upload_job = get_upload_job_by_id(session, upload_job.id)

        assert persisted_video is not None
        assert persisted_video.creator_id == creator.id
        assert persisted_video.title == "My first upload"
        assert persisted_video.original_storage_path == "uploads/1/clip.mp4"
        assert persisted_video.hls_manifest_path is None
        assert persisted_video.cover_image_path is None
        assert persisted_video.visibility is VideoVisibility.PUBLIC
        assert persisted_video.published_at is None
        assert persisted_video.view_count == 0

        assert persisted_upload_job is not None
        assert persisted_upload_job.video_id == video.id
        assert persisted_upload_job.status is UploadJobStatus.PENDING
        assert persisted_upload_job.failure_message is None
        assert persisted_upload_job.started_at is None
        assert persisted_upload_job.finished_at is None

        video_record = VideoRecord.model_validate(persisted_video)
        upload_job_record = UploadJobRecord.model_validate(persisted_upload_job)

        assert video_record.original_filename == "clip.mp4"
        assert video_record.visibility is VideoVisibility.PUBLIC
        assert video_record.published_at is None
        assert video_record.view_count == 0
        assert upload_job_record.status is UploadJobStatus.PENDING
    finally:
        session.close()


def test_list_feed_videos_filters_to_ready_videos_and_paginates(tmp_path: Path) -> None:
    session = create_test_session(tmp_path)
    now = datetime.now(UTC)

    try:
        creator = create_creator(session)
        create_video_record(
            session,
            creator.id,
            title="Not ready",
            original_storage_path="uploads/1/not-ready.mp4",
        )
        create_video_record(
            session,
            creator.id,
            title="Ready oldest",
            original_storage_path="uploads/1/ready-oldest.mp4",
            published_at=now - timedelta(minutes=30),
            hls_manifest_path="hls/1/index.m3u8",
            cover_image_path="covers/1/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            title="Ready middle",
            original_storage_path="uploads/1/ready-middle.mp4",
            published_at=now - timedelta(minutes=20),
            hls_manifest_path="hls/2/index.m3u8",
            cover_image_path="covers/2/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            visibility=VideoVisibility.HIDDEN,
            title="Hidden ready",
            original_storage_path="uploads/1/hidden-ready.mp4",
            published_at=now - timedelta(minutes=15),
            hls_manifest_path="hls/9/index.m3u8",
            cover_image_path="covers/9/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            title="Ready newest",
            original_storage_path="uploads/1/ready-newest.mp4",
            published_at=now - timedelta(minutes=10),
            hls_manifest_path="hls/3/index.m3u8",
            cover_image_path="covers/3/cover.jpg",
        )
        session.commit()

        first_page = list_feed_videos(session, page=1, page_size=2)
        second_page = list_feed_videos(session, page=2, page_size=2)

        assert [video.title for video in first_page.items] == ["Ready newest", "Ready middle"]
        assert [video.title for video in second_page.items] == ["Ready oldest"]
        assert first_page.total_items == 3
        assert first_page.total_pages == 2
        assert first_page.has_more is True
        assert second_page.has_more is False
    finally:
        session.close()


def test_list_feed_videos_combines_freshness_and_hotness_deterministically(
    tmp_path: Path,
) -> None:
    session = create_test_session(tmp_path)
    now = datetime.now(UTC)

    try:
        creator = create_creator(session)
        create_video_record(
            session,
            creator.id,
            title="Freshest",
            original_storage_path="uploads/1/freshest.mp4",
            published_at=now,
            view_count=0,
            hls_manifest_path="hls/10/index.m3u8",
            cover_image_path="covers/10/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            title="Hotter recent",
            original_storage_path="uploads/1/hotter-recent.mp4",
            published_at=now - timedelta(minutes=4),
            view_count=2,
            hls_manifest_path="hls/11/index.m3u8",
            cover_image_path="covers/11/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            title="Older capped hotness",
            original_storage_path="uploads/1/older-hot.mp4",
            published_at=now - timedelta(hours=2),
            view_count=999,
            hls_manifest_path="hls/12/index.m3u8",
            cover_image_path="covers/12/cover.jpg",
        )
        session.commit()

        first_read = list_feed_videos(session, page=1, page_size=10)
        second_read = list_feed_videos(session, page=1, page_size=10)

        expected_order = ["Hotter recent", "Freshest", "Older capped hotness"]
        assert [video.title for video in first_read.items] == expected_order
        assert [video.id for video in second_read.items] == [video.id for video in first_read.items]
    finally:
        session.close()


def test_list_feed_videos_excludes_invalid_asset_paths(tmp_path: Path) -> None:
    session = create_test_session(tmp_path)
    now = datetime.now(UTC)

    try:
        creator = create_creator(session)
        create_video_record(
            session,
            creator.id,
            title="Invalid asset paths",
            original_storage_path="uploads/1/invalid.mp4",
            published_at=now,
            hls_manifest_path="broken/index.m3u8",
            cover_image_path="covers/1/cover.jpg",
        )
        create_video_record(
            session,
            creator.id,
            title="Valid ready video",
            original_storage_path="uploads/1/valid.mp4",
            published_at=now - timedelta(minutes=1),
            hls_manifest_path="hls/2/index.m3u8",
            cover_image_path="covers/2/cover.jpg",
        )
        session.commit()

        feed_page = list_feed_videos(session, page=1, page_size=10)

        assert [video.title for video in feed_page.items] == ["Valid ready video"]
    finally:
        session.close()


def test_hidden_video_is_not_publicly_visible_or_feed_ready(tmp_path: Path) -> None:
    session = create_test_session(tmp_path)
    now = datetime.now(UTC)

    try:
        creator = create_creator(session)
        video = create_video(
            session,
            CreateVideoInput(
                creator_id=creator.id,
                title="Hidden ready candidate",
                caption=None,
                original_filename="hidden.mp4",
                original_content_type="video/mp4",
                original_file_size=2048,
                original_storage_path="uploads/1/hidden.mp4",
                visibility=VideoVisibility.HIDDEN,
                published_at=now,
            ),
        )
        video.hls_manifest_path = "hls/1/index.m3u8"
        video.cover_image_path = "covers/1/cover.jpg"
        session.commit()

        persisted_video = get_video_by_id(session, video.id)

        assert persisted_video is not None
        assert is_video_publicly_visible(persisted_video) is False
        assert is_video_ready_for_feed(persisted_video) is False
    finally:
        session.close()


def test_process_upload_job_marks_video_as_feed_ready_on_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session_factory = create_test_session_factory(tmp_path)
    storage_root = tmp_path / "storage"
    media_runtime = MediaRuntime(
        ffmpeg_binary="ffmpeg",
        storage_root=storage_root,
        uploads_dir=storage_root / "uploads",
        hls_dir=storage_root / "hls",
        covers_dir=storage_root / "covers",
        hls_public_path="/media/hls",
        covers_public_path="/media/covers",
    )
    media_runtime.ensure_directories()

    def fake_run_ffmpeg_pipeline(_media_runtime, _source_path, video_id: int) -> ProcessedVideoAssets:
        hls_dir = media_runtime.hls_dir_for(str(video_id))
        cover_dir = media_runtime.cover_dir_for(str(video_id))
        hls_dir.mkdir(parents=True, exist_ok=True)
        cover_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = hls_dir / "index.m3u8"
        manifest_path.write_text("#EXTM3U\n", encoding="utf-8")
        cover_path = cover_dir / "cover.jpg"
        cover_path.write_bytes(b"cover")

        return ProcessedVideoAssets(
            hls_manifest_path=manifest_path.relative_to(media_runtime.storage_root).as_posix(),
            cover_image_path=cover_path.relative_to(media_runtime.storage_root).as_posix(),
        )

    monkeypatch.setattr(
        "app.domains.videos.processing.run_ffmpeg_pipeline",
        fake_run_ffmpeg_pipeline,
    )

    session = session_factory()
    try:
        creator = create_creator(session)
        video = create_video(
            session,
            CreateVideoInput(
                creator_id=creator.id,
                title="Ready after processing",
                caption=None,
                original_filename="source.mp4",
                original_content_type="video/mp4",
                original_file_size=len(b"fake-video"),
                original_storage_path="uploads/pending/source.mp4",
            ),
        )
        source_dir = media_runtime.upload_dir_for(str(video.id))
        source_dir.mkdir(parents=True, exist_ok=True)
        source_path = source_dir / "source.mp4"
        source_path.write_bytes(b"fake-video")
        video.original_storage_path = source_path.relative_to(media_runtime.storage_root).as_posix()
        upload_job = create_upload_job(session, CreateUploadJobInput(video_id=video.id))
        video_id = video.id
        upload_job_id = upload_job.id
        session.commit()
    finally:
        session.close()

    process_upload_job(session_factory, media_runtime, upload_job_id)

    verification_session = session_factory()
    try:
        persisted_video = get_video_by_id(verification_session, video_id)
        persisted_upload_job = get_upload_job_by_id(verification_session, upload_job_id)

        assert persisted_video is not None
        assert persisted_upload_job is not None
        assert persisted_upload_job.status is UploadJobStatus.READY
        assert persisted_video.published_at is not None
        assert persisted_video.view_count == 0
        assert is_video_ready_for_feed(persisted_video) is True
    finally:
        verification_session.close()
