from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domains.videos.models import UploadJobStatus, VideoVisibility


class VideoRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creator_id: int
    title: str
    caption: str | None
    original_filename: str
    original_content_type: str | None
    original_file_size: int
    original_storage_path: str
    hls_manifest_path: str | None
    cover_image_path: str | None
    visibility: VideoVisibility
    published_at: datetime | None
    view_count: int
    created_at: datetime
    updated_at: datetime


class UploadJobRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: UploadJobStatus
    failure_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VideoUploadAcceptedResponse(BaseModel):
    video_id: int
    upload_job_id: int
    status: UploadJobStatus


class UploadJobStatusResponse(BaseModel):
    upload_job_id: int
    video_id: int
    status: UploadJobStatus
    failure_message: str | None
    hls_manifest_url: str | None
    cover_image_url: str | None


class FeedCreatorSummary(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str | None


class AdminVideoCreatorSummary(BaseModel):
    id: int
    email: str
    username: str
    display_name: str


class AdminVideoListItemResponse(BaseModel):
    id: int
    title: str
    caption: str | None
    creator: AdminVideoCreatorSummary
    visibility: VideoVisibility
    latest_upload_job_id: int | None
    latest_upload_status: UploadJobStatus | None
    failure_message: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminVideoListResponse(BaseModel):
    items: list[AdminVideoListItemResponse]
    page: int
    page_size: int
    has_more: bool
    total_items: int


class AdminVideoVisibilityUpdateRequest(BaseModel):
    visibility: VideoVisibility


class AdminVideoVisibilityUpdateResponse(BaseModel):
    video_id: int
    visibility: VideoVisibility


class FeedVideoItem(BaseModel):
    id: int
    title: str
    caption: str | None
    hls_manifest_url: str
    cover_image_url: str
    creator: FeedCreatorSummary


class VideoFeedResponse(BaseModel):
    items: list[FeedVideoItem]
    page: int
    page_size: int
    has_more: bool


class VideoPlaybackStartResponse(BaseModel):
    video_id: int
    view_count: int
