"""Contenedor de dependencias (inyección simple sin framework extra)."""

from functools import lru_cache

from app.ai.highlight_detector import HighlightDetector
from app.ai.whisper_service import WhisperService
from app.config.settings import get_settings
from app.services.clip_service import ClipService
from app.services.video_service import VideoService
from app.storage.storage_service import StorageService
from app.subtitle.subtitle_service import SubtitleService
from app.video.face_tracker import FaceTracker
from app.video.ffmpeg_service import FFmpegService
from app.video.layout_service import LayoutService


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService(get_settings())


@lru_cache
def get_ffmpeg_service() -> FFmpegService:
    return FFmpegService(get_settings())


@lru_cache
def get_whisper_service() -> WhisperService:
    return WhisperService(get_settings())


@lru_cache
def get_subtitle_service() -> SubtitleService:
    return SubtitleService()


@lru_cache
def get_highlight_detector() -> HighlightDetector:
    return HighlightDetector(get_settings())


@lru_cache
def get_face_tracker() -> FaceTracker:
    return FaceTracker()


@lru_cache
def get_layout_service() -> LayoutService:
    return LayoutService(
        ffmpeg=get_ffmpeg_service(),
        face_tracker=get_face_tracker(),
    )


@lru_cache
def get_clip_service() -> ClipService:
    return ClipService(
        ffmpeg=get_ffmpeg_service(),
        subtitle=get_subtitle_service(),
        storage=get_storage_service(),
        layout=get_layout_service(),
    )


@lru_cache
def get_video_service() -> VideoService:
    return VideoService(
        settings=get_settings(),
        storage=get_storage_service(),
        ffmpeg=get_ffmpeg_service(),
        whisper=get_whisper_service(),
        highlight_detector=get_highlight_detector(),
        clip_service=get_clip_service(),
        layout=get_layout_service(),
    )


@lru_cache
def get_content_enrichment_service():
    from app.modules.content_ai.enrichment import ContentEnrichmentService

    return ContentEnrichmentService()


@lru_cache
def get_jobs_service():
    from app.modules.jobs.service import JobsService

    return JobsService()


@lru_cache
def get_credits_service():
    from app.modules.credits.service import CreditsService

    return CreditsService()
