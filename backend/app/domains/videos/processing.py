from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.core.media import MediaRuntime
from app.domains.videos.service import (
    get_upload_job_by_id,
    get_video_by_id,
    mark_upload_job_failed,
    mark_upload_job_processing,
    mark_upload_job_ready,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessedVideoAssets:
    hls_manifest_path: str
    cover_image_path: str


def _cleanup_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _run_command(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "FFmpeg command failed."
        raise RuntimeError(stderr)


def run_ffmpeg_pipeline(
    media_runtime: MediaRuntime,
    source_path: Path,
    video_id: int,
) -> ProcessedVideoAssets:
    hls_dir = media_runtime.hls_dir_for(str(video_id))
    cover_dir = media_runtime.cover_dir_for(str(video_id))
    _cleanup_directory(hls_dir)
    _cleanup_directory(cover_dir)
    hls_dir.mkdir(parents=True, exist_ok=True)
    cover_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = hls_dir / "index.m3u8"
    segment_pattern = hls_dir / "segment_%03d.ts"
    cover_path = cover_dir / "cover.jpg"

    _run_command(
        [
            media_runtime.ffmpeg_binary,
            "-y",
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-start_number",
            "0",
            "-hls_time",
            "4",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(segment_pattern),
            str(manifest_path),
        ]
    )
    _run_command(
        [
            media_runtime.ffmpeg_binary,
            "-y",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(cover_path),
        ]
    )

    return ProcessedVideoAssets(
        hls_manifest_path=manifest_path.relative_to(media_runtime.storage_root).as_posix(),
        cover_image_path=cover_path.relative_to(media_runtime.storage_root).as_posix(),
    )


def process_upload_job(
    session_factory: sessionmaker,
    media_runtime: MediaRuntime,
    upload_job_id: int,
) -> None:
    session: Session = session_factory()
    try:
        logger.info("Starting upload job processing.", extra={"upload_job_id": upload_job_id})
        upload_job = get_upload_job_by_id(session, upload_job_id)
        if upload_job is None:
            logger.warning(
                "Upload job disappeared before processing started.",
                extra={"upload_job_id": upload_job_id},
            )
            return

        video = get_video_by_id(session, upload_job.video_id)
        if video is None:
            mark_upload_job_failed(upload_job, "Associated video record was not found.")
            session.commit()
            logger.error(
                "Upload job failed because the associated video was not found.",
                extra={"upload_job_id": upload_job_id},
            )
            return

        mark_upload_job_processing(upload_job)
        session.commit()
        logger.info(
            "Upload job entered processing state.",
            extra={"upload_job_id": upload_job.id, "video_id": video.id},
        )

        source_path = media_runtime.storage_root / video.original_storage_path
        if not source_path.exists():
            raise RuntimeError("Uploaded source video was not found.")

        processed_assets = run_ffmpeg_pipeline(media_runtime, source_path, video.id)

        upload_job = get_upload_job_by_id(session, upload_job_id)
        video = get_video_by_id(session, video.id)
        if upload_job is None or video is None:
            return

        video.hls_manifest_path = processed_assets.hls_manifest_path
        video.cover_image_path = processed_assets.cover_image_path
        if video.published_at is None:
            video.published_at = datetime.now(UTC)
        mark_upload_job_ready(upload_job)
        session.commit()
        logger.info(
            "Upload job finished successfully.",
            extra={"upload_job_id": upload_job.id, "video_id": video.id},
        )
    except Exception as exc:
        session.rollback()
        upload_job = get_upload_job_by_id(session, upload_job_id)
        if upload_job is not None:
            mark_upload_job_failed(upload_job, str(exc))
            session.commit()
            logger.exception(
                "Upload job failed during processing.",
                extra={"upload_job_id": upload_job.id, "video_id": upload_job.video_id},
            )
        else:
            logger.exception(
                "Upload job failed before it could be reloaded for failure persistence.",
                extra={"upload_job_id": upload_job_id},
            )
    finally:
        session.close()
