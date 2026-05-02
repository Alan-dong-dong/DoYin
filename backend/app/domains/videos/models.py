from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.domains.users.models import User


class UploadJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoVisibility(str, Enum):
    PUBLIC = "public"
    HIDDEN = "hidden"


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120))
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    original_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_file_size: Mapped[int] = mapped_column(Integer)
    original_storage_path: Mapped[str] = mapped_column(String(1024))
    hls_manifest_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    visibility: Mapped[VideoVisibility] = mapped_column(
        SqlEnum(
            VideoVisibility,
            name="video_visibility",
            native_enum=False,
            validate_strings=True,
        ),
        default=VideoVisibility.PUBLIC,
        server_default=VideoVisibility.PUBLIC.value,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    creator: Mapped["User"] = relationship()
    upload_jobs: Mapped[list["UploadJob"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="UploadJob.created_at",
    )


class UploadJob(Base):
    __tablename__ = "upload_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[UploadJobStatus] = mapped_column(
        SqlEnum(
            UploadJobStatus,
            name="upload_job_status",
            native_enum=False,
            validate_strings=True,
        ),
        default=UploadJobStatus.PENDING,
        server_default=UploadJobStatus.PENDING.value,
    )
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    video: Mapped[Video] = relationship(back_populates="upload_jobs")
