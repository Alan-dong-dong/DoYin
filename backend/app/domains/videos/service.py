from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domains.videos.models import UploadJob, UploadJobStatus, Video, VideoVisibility

_FEED_VIEW_WEIGHT_SECONDS = 5 * 60
_MAX_FEED_VIEW_BONUS = 12


@dataclass(frozen=True, slots=True)
class CreateVideoInput:
    creator_id: int
    title: str
    caption: str | None
    original_filename: str
    original_content_type: str | None
    original_file_size: int
    original_storage_path: str
    visibility: VideoVisibility = VideoVisibility.PUBLIC
    published_at: datetime | None = None
    view_count: int = 0


@dataclass(frozen=True, slots=True)
class CreateUploadJobInput:
    video_id: int
    status: UploadJobStatus = UploadJobStatus.PENDING


@dataclass(frozen=True, slots=True)
class FeedPage:
    items: list[Video]
    page: int
    page_size: int
    has_more: bool
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class AdminVideoFilters:
    keyword: str | None = None
    upload_status: UploadJobStatus | None = None
    visibility: VideoVisibility | None = None


@dataclass(frozen=True, slots=True)
class AdminVideoListItem:
    video: Video
    latest_upload_job: UploadJob | None


@dataclass(frozen=True, slots=True)
class AdminVideoPage:
    items: list[AdminVideoListItem]
    page: int
    page_size: int
    has_more: bool
    total_items: int
    total_pages: int


def create_video(db: Session, payload: CreateVideoInput) -> Video:
    video = Video(
        creator_id=payload.creator_id,
        title=payload.title,
        caption=payload.caption,
        original_filename=payload.original_filename,
        original_content_type=payload.original_content_type,
        original_file_size=payload.original_file_size,
        original_storage_path=payload.original_storage_path,
        visibility=payload.visibility,
        published_at=payload.published_at,
        view_count=payload.view_count,
    )
    db.add(video)
    db.flush()
    return video


def get_video_by_id(db: Session, video_id: int) -> Video | None:
    return db.scalar(select(Video).where(Video.id == video_id))


def create_upload_job(db: Session, payload: CreateUploadJobInput) -> UploadJob:
    upload_job = UploadJob(
        video_id=payload.video_id,
        status=payload.status,
    )
    db.add(upload_job)
    db.flush()
    return upload_job


def get_upload_job_by_id(db: Session, upload_job_id: int) -> UploadJob | None:
    return db.scalar(select(UploadJob).where(UploadJob.id == upload_job_id))


def get_latest_upload_job(video: Video) -> UploadJob | None:
    if not video.upload_jobs:
        return None

    return video.upload_jobs[-1]


def is_video_publicly_visible(video: Video) -> bool:
    return video.visibility is VideoVisibility.PUBLIC


def is_video_ready_for_feed(video: Video) -> bool:
    return (
        is_video_publicly_visible(video)
        and
        video.published_at is not None
        and _has_public_asset_path(video.hls_manifest_path, "hls")
        and _has_public_asset_path(video.cover_image_path, "covers")
    )


def _has_public_asset_path(storage_path: str | None, root: str) -> bool:
    if not storage_path:
        return False

    parts = Path(storage_path).parts
    return len(parts) >= 2 and parts[0] == root


def _feed_score(video: Video) -> float:
    published_at = video.published_at
    if published_at is None:
        return float("-inf")
    hotness_bonus = min(video.view_count, _MAX_FEED_VIEW_BONUS) * _FEED_VIEW_WEIGHT_SECONDS
    return published_at.timestamp() + hotness_bonus


def _feed_sort_key(video: Video) -> tuple[float, float, int, int]:
    published_timestamp = video.published_at.timestamp() if video.published_at else float("-inf")
    return (
        _feed_score(video),
        published_timestamp,
        video.view_count,
        video.id,
    )


def _matches_admin_keyword(video: Video, keyword: str) -> bool:
    normalized_keyword = keyword.strip().lower()
    if not normalized_keyword:
        return True

    haystacks = [
        video.title,
        video.creator.email,
        video.creator.username,
        video.creator.display_name,
    ]
    return any(normalized_keyword in value.lower() for value in haystacks)


def _matches_admin_filters(video: Video, filters: AdminVideoFilters) -> bool:
    latest_upload_job = get_latest_upload_job(video)
    if filters.visibility is not None and video.visibility is not filters.visibility:
        return False

    if filters.upload_status is not None:
        if latest_upload_job is None or latest_upload_job.status is not filters.upload_status:
            return False

    if filters.keyword and not _matches_admin_keyword(video, filters.keyword):
        return False

    return True


def list_feed_videos(db: Session, page: int, page_size: int) -> FeedPage:
    if page < 1:
        raise ValueError("Feed page must be greater than or equal to 1.")
    if page_size < 1:
        raise ValueError("Feed page size must be greater than or equal to 1.")

    videos = list(db.scalars(select(Video)))
    eligible_videos = [video for video in videos if is_video_ready_for_feed(video)]
    ordered_videos = sorted(eligible_videos, key=_feed_sort_key, reverse=True)

    offset = (page - 1) * page_size
    items = ordered_videos[offset : offset + page_size]
    total_items = len(ordered_videos)
    total_pages = ceil(total_items / page_size) if total_items else 0

    return FeedPage(
        items=items,
        page=page,
        page_size=page_size,
        has_more=offset + page_size < total_items,
        total_items=total_items,
        total_pages=total_pages,
    )


def list_admin_videos(
    db: Session,
    *,
    page: int,
    page_size: int,
    filters: AdminVideoFilters | None = None,
) -> AdminVideoPage:
    if page < 1:
        raise ValueError("Admin page must be greater than or equal to 1.")
    if page_size < 1:
        raise ValueError("Admin page size must be greater than or equal to 1.")

    resolved_filters = filters or AdminVideoFilters()
    videos = list(
        db.scalars(
            select(Video).options(
                selectinload(Video.creator),
                selectinload(Video.upload_jobs),
            )
        )
    )
    filtered_videos = [
        video for video in videos if _matches_admin_filters(video, resolved_filters)
    ]
    ordered_videos = sorted(filtered_videos, key=lambda video: video.id, reverse=True)

    offset = (page - 1) * page_size
    paginated_videos = ordered_videos[offset : offset + page_size]
    total_items = len(ordered_videos)
    total_pages = ceil(total_items / page_size) if total_items else 0

    return AdminVideoPage(
        items=[
            AdminVideoListItem(
                video=video,
                latest_upload_job=get_latest_upload_job(video),
            )
            for video in paginated_videos
        ],
        page=page,
        page_size=page_size,
        has_more=offset + page_size < total_items,
        total_items=total_items,
        total_pages=total_pages,
    )


def set_video_visibility(video: Video, visibility: VideoVisibility) -> Video:
    video.visibility = visibility
    return video


def mark_upload_job_processing(upload_job: UploadJob) -> None:
    upload_job.status = UploadJobStatus.PROCESSING
    upload_job.failure_message = None
    upload_job.started_at = datetime.now(UTC)
    upload_job.finished_at = None


def mark_upload_job_ready(upload_job: UploadJob) -> None:
    upload_job.status = UploadJobStatus.READY
    upload_job.failure_message = None
    upload_job.finished_at = datetime.now(UTC)


def mark_upload_job_failed(upload_job: UploadJob, failure_message: str) -> None:
    upload_job.status = UploadJobStatus.FAILED
    upload_job.failure_message = failure_message
    upload_job.finished_at = datetime.now(UTC)


def record_video_playback_start(video: Video) -> int:
    if not is_video_ready_for_feed(video):
        raise ValueError("Only ready videos can record playback starts.")

    video.view_count += 1
    return video.view_count
