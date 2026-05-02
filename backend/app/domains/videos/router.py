from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.media import MediaRuntime, get_media_runtime
from app.db.runtime import get_db_session
from app.domains.auth.security import get_current_user, require_admin_user
from app.domains.users.models import User
from app.domains.videos.models import UploadJobStatus, VideoVisibility
from app.domains.videos.processing import process_upload_job
from app.domains.videos.schemas import (
    AdminVideoCreatorSummary,
    AdminVideoListItemResponse,
    AdminVideoListResponse,
    AdminVideoVisibilityUpdateRequest,
    AdminVideoVisibilityUpdateResponse,
    FeedCreatorSummary,
    FeedVideoItem,
    UploadJobStatusResponse,
    VideoFeedResponse,
    VideoPlaybackStartResponse,
    VideoUploadAcceptedResponse,
)
from app.domains.videos.service import (
    AdminVideoFilters,
    CreateUploadJobInput,
    CreateVideoInput,
    create_upload_job,
    create_video,
    get_upload_job_by_id,
    get_latest_upload_job,
    get_video_by_id,
    is_video_ready_for_feed,
    list_admin_videos,
    list_feed_videos,
    record_video_playback_start,
    set_video_visibility,
)

router = APIRouter(prefix="/videos", tags=["videos"])
logger = logging.getLogger(__name__)

_SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".webm",
    ".mkv",
}


def _validate_upload(title: str, video_file: UploadFile) -> tuple[str, str]:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title is required.",
        )

    original_filename = Path(video_file.filename or "").name
    suffix = Path(original_filename).suffix.lower()
    content_type = video_file.content_type or ""

    is_supported_content_type = content_type.startswith("video/")
    is_supported_extension = suffix in _SUPPORTED_VIDEO_EXTENSIONS
    if not original_filename or not (is_supported_content_type or is_supported_extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A supported video file is required.",
        )

    return normalized_title, suffix or ".upload"


def _build_hls_url(media_runtime: MediaRuntime, storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    try:
        relative_path = Path(storage_path).relative_to("hls").as_posix()
    except ValueError:
        return None
    return media_runtime.build_hls_url(relative_path)


def _build_cover_url(media_runtime: MediaRuntime, storage_path: str | None) -> str | None:
    if not storage_path:
        return None
    try:
        relative_path = Path(storage_path).relative_to("covers").as_posix()
    except ValueError:
        return None
    return media_runtime.build_cover_url(relative_path)


def _build_feed_video_item(video, media_runtime: MediaRuntime) -> FeedVideoItem | None:
    hls_manifest_url = _build_hls_url(media_runtime, video.hls_manifest_path)
    cover_image_url = _build_cover_url(media_runtime, video.cover_image_path)
    if hls_manifest_url is None or cover_image_url is None:
        logger.warning(
            "Skipping feed candidate with unusable playback asset references.",
            extra={
                "video_id": video.id,
                "hls_manifest_path": video.hls_manifest_path,
                "cover_image_path": video.cover_image_path,
            },
        )
        return None

    return FeedVideoItem(
        id=video.id,
        title=video.title,
        caption=video.caption,
        hls_manifest_url=hls_manifest_url,
        cover_image_url=cover_image_url,
        creator=FeedCreatorSummary(
            id=video.creator.id,
            username=video.creator.username,
            display_name=video.creator.display_name,
            avatar_url=video.creator.avatar_url,
        ),
    )


def _build_admin_video_item_response(video) -> AdminVideoListItemResponse:
    latest_upload_job = get_latest_upload_job(video)
    return AdminVideoListItemResponse(
        id=video.id,
        title=video.title,
        caption=video.caption,
        creator=AdminVideoCreatorSummary(
            id=video.creator.id,
            email=video.creator.email,
            username=video.creator.username,
            display_name=video.creator.display_name,
        ),
        visibility=video.visibility,
        latest_upload_job_id=latest_upload_job.id if latest_upload_job is not None else None,
        latest_upload_status=latest_upload_job.status if latest_upload_job is not None else None,
        failure_message=latest_upload_job.failure_message if latest_upload_job is not None else None,
        published_at=video.published_at,
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


@router.get("/feed", response_model=VideoFeedResponse)
def read_video_feed(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=20)] = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    media_runtime: MediaRuntime = Depends(get_media_runtime),
) -> VideoFeedResponse:
    del current_user

    feed_page = list_feed_videos(db, page=page, page_size=page_size)
    items: list[FeedVideoItem] = []
    for video in feed_page.items:
        item = _build_feed_video_item(video, media_runtime)
        if item is not None:
            items.append(item)

    return VideoFeedResponse(
        items=items,
        page=feed_page.page,
        page_size=feed_page.page_size,
        has_more=feed_page.has_more,
    )


@router.get("/admin", response_model=AdminVideoListResponse)
def read_admin_video_inventory(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    q: str | None = None,
    processing_status: Annotated[UploadJobStatus | None, Query(alias="status")] = None,
    visibility: VideoVisibility | None = None,
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
) -> AdminVideoListResponse:
    del admin_user

    admin_page = list_admin_videos(
        db,
        page=page,
        page_size=page_size,
        filters=AdminVideoFilters(
            keyword=q,
            upload_status=processing_status,
            visibility=visibility,
        ),
    )

    return AdminVideoListResponse(
        items=[
            _build_admin_video_item_response(item.video)
            for item in admin_page.items
        ],
        page=admin_page.page,
        page_size=admin_page.page_size,
        has_more=admin_page.has_more,
        total_items=admin_page.total_items,
    )


@router.post(
    "/uploads",
    response_model=VideoUploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_video_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    title: Annotated[str, Form(...)],
    video_file: Annotated[UploadFile, File(...)],
    caption: Annotated[str | None, Form()] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    media_runtime: MediaRuntime = Depends(get_media_runtime),
) -> VideoUploadAcceptedResponse:
    normalized_title, suffix = _validate_upload(title, video_file)
    normalized_caption = caption.strip() if caption is not None else None
    if normalized_caption == "":
        normalized_caption = None

    video = create_video(
        db,
        CreateVideoInput(
            creator_id=current_user.id,
            title=normalized_title,
            caption=normalized_caption,
            original_filename=Path(video_file.filename or "").name,
            original_content_type=video_file.content_type,
            original_file_size=0,
            original_storage_path="pending",
        ),
    )

    upload_dir = media_runtime.upload_dir_for(str(video.id))
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_path = upload_dir / f"source{suffix}"

    try:
        with original_path.open("wb") as destination:
            shutil.copyfileobj(video_file.file, destination)
        file_size = original_path.stat().st_size
        if file_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A supported video file is required.",
            )

        video.original_file_size = file_size
        video.original_storage_path = original_path.relative_to(
            media_runtime.storage_root
        ).as_posix()
        upload_job = create_upload_job(
            db,
            CreateUploadJobInput(video_id=video.id),
        )
        db.commit()
        background_tasks.add_task(
            process_upload_job,
            request.app.state.db_session_factory,
            media_runtime,
            upload_job.id,
        )
        logger.info(
            "Accepted video upload and queued background processing.",
            extra={"video_id": video.id, "upload_job_id": upload_job.id, "creator_id": current_user.id},
        )
    except HTTPException:
        db.rollback()
        logger.warning(
            "Rejected video upload during validation or storage.",
            extra={"creator_id": current_user.id, "filename": Path(video_file.filename or "").name},
        )
        if original_path.exists():
            original_path.unlink()
        if upload_dir.exists() and not any(upload_dir.iterdir()):
            upload_dir.rmdir()
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error while accepting video upload.",
            extra={"creator_id": current_user.id, "filename": Path(video_file.filename or "").name},
        )
        if original_path.exists():
            original_path.unlink()
        if upload_dir.exists() and not any(upload_dir.iterdir()):
            upload_dir.rmdir()
        raise
    finally:
        video_file.file.close()

    return VideoUploadAcceptedResponse(
        video_id=video.id,
        upload_job_id=upload_job.id,
        status=upload_job.status,
    )


@router.get(
    "/uploads/{upload_job_id}",
    response_model=UploadJobStatusResponse,
)
def read_upload_job_status(
    upload_job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
    media_runtime: MediaRuntime = Depends(get_media_runtime),
) -> UploadJobStatusResponse:
    upload_job = get_upload_job_by_id(db, upload_job_id)
    if upload_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload job was not found.",
        )

    video = get_video_by_id(db, upload_job.video_id)
    if video is None or video.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload job was not found.",
        )

    return UploadJobStatusResponse(
        upload_job_id=upload_job.id,
        video_id=video.id,
        status=upload_job.status,
        failure_message=upload_job.failure_message,
        hls_manifest_url=_build_hls_url(media_runtime, video.hls_manifest_path),
        cover_image_url=_build_cover_url(media_runtime, video.cover_image_path),
    )


@router.post(
    "/{video_id}/playbacks",
    response_model=VideoPlaybackStartResponse,
)
def record_video_playback(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> VideoPlaybackStartResponse:
    del current_user

    video = get_video_by_id(db, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video was not found.",
        )

    if not is_video_ready_for_feed(video):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video is not ready for playback.",
        )

    view_count = record_video_playback_start(video)
    db.commit()

    return VideoPlaybackStartResponse(
        video_id=video.id,
        view_count=view_count,
    )


@router.patch(
    "/admin/{video_id}/visibility",
    response_model=AdminVideoVisibilityUpdateResponse,
)
def update_admin_video_visibility(
    video_id: int,
    payload: AdminVideoVisibilityUpdateRequest,
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
) -> AdminVideoVisibilityUpdateResponse:
    del admin_user

    video = get_video_by_id(db, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video was not found.",
        )

    set_video_visibility(video, payload.visibility)
    db.commit()

    return AdminVideoVisibilityUpdateResponse(
        video_id=video.id,
        visibility=video.visibility,
    )
