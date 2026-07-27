"""Composición de layouts: formatos sociales + entrevista vertical split."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from app.schemas.options import (
    FORMAT_RESOLUTIONS,
    ClipFormat,
    ContentMode,
    FillMode,
    InterviewLayout,
    ProcessOptions,
)
from app.utils.logger import get_logger
from app.video.face_tracker import ActiveSegment, FaceBox, FaceTracker, SpeakerRegions
from app.video.ffmpeg_service import FFmpegService
from app.video.framing import compute_cover_crop, speaker_panel_crop

logger = get_logger(__name__)


class LayoutService:
    """Aplica recortes / stacks según modo de contenido y formato de salida."""

    def __init__(self, ffmpeg: FFmpegService, face_tracker: Optional[FaceTracker] = None):
        self.ffmpeg = ffmpeg
        self.face_tracker = face_tracker or FaceTracker()

    def render_clip(
        self,
        source: Path,
        output: Path,
        *,
        start: float,
        end: float,
        fmt: ClipFormat,
        options: ProcessOptions,
        regions: Optional[SpeakerRegions] = None,
        activity: Optional[Sequence[ActiveSegment]] = None,
    ) -> Path:
        out_w, out_h = FORMAT_RESOLUTIONS[fmt]
        is_verticalish = out_h > out_w
        use_interview = (
            options.content_mode in (ContentMode.INTERVIEW, ContentMode.MULTI_SPEAKER)
            and is_verticalish
            and options.interview_layout != InterviewLayout.SINGLE_FOLLOW
        )

        if use_interview:
            return self._render_interview_stack(
                source,
                output,
                start=start,
                end=end,
                out_w=out_w,
                out_h=out_h,
                options=options,
                regions=regions,
                activity=activity,
            )

        src_w, src_h = self._source_size(source, regions)
        face = None
        if regions and regions.primary:
            face = regions.primary
        elif options.fill_mode == FillMode.SMART_CROP or options.content_mode != ContentMode.MONOLOGUE:
            try:
                regs, _ = self.face_tracker.analyze_video(
                    source,
                    start=start,
                    end=end,
                    max_speakers=1,
                    sample_every_sec=1.5,
                    max_samples=8,
                )
                face = regs.primary
                if regs.frame_width and regs.frame_height:
                    src_w, src_h = regs.frame_width, regs.frame_height
            except Exception as exc:  # noqa: BLE001
                logger.warning("Face detect falló: %s", exc)

        # Crop grande adaptado al AR de salida (alejado → sin pixelar)
        focus_box = None
        if options.fill_mode == FillMode.SMART_CROP:
            if face:
                focus_box = compute_cover_crop(
                    src_w, src_h, out_w, out_h,
                    face.cx, face.cy - face.h * 0.15,
                    contain=face,
                    zoom=1.0,
                )
            else:
                focus_box = compute_cover_crop(
                    src_w, src_h, out_w, out_h,
                    src_w / 2, src_h / 2,
                    zoom=1.0,
                )
            logger.info(
                "Smart crop fuente %dx%d → región %s → salida %dx%d",
                src_w, src_h, focus_box, out_w, out_h,
            )

        return self.ffmpeg.cut_and_reformat(
            source,
            output,
            start=start,
            end=end,
            out_w=out_w,
            out_h=out_h,
            fill_mode=options.fill_mode.value,
            focus_box=focus_box,
            src_size=(src_w, src_h),
            mirror_horizontal=options.mirror_horizontal,
        )

    def analyze_speakers(
        self,
        video_path: Path,
        options: ProcessOptions,
        on_progress=None,
    ) -> Tuple[Optional[SpeakerRegions], List[ActiveSegment]]:
        # Monólogo: pocas muestras bastan para el crop
        # Entrevista: más muestras, pero con tope duro
        is_interview = options.content_mode in (
            ContentMode.INTERVIEW,
            ContentMode.MULTI_SPEAKER,
        )
        max_sp = 1 if options.content_mode == ContentMode.MONOLOGUE else 2
        max_samples = 48 if is_interview else 12
        sample_every = 1.2 if is_interview else 2.5

        # Letterbox no necesita rostros en el análisis global
        if options.fill_mode == FillMode.LETTERBOX and not is_interview:
            logger.info("Skip face analysis (letterbox + monólogo)")
            return None, []

        try:
            regions, activity = self.face_tracker.analyze_video(
                video_path,
                max_speakers=max_sp,
                sample_every_sec=sample_every,
                max_samples=max_samples,
                on_progress=on_progress,
            )
            return regions, activity
        except Exception as exc:  # noqa: BLE001
            logger.warning("Análisis de hablantes falló: %s", exc)
            return None, []

    def _source_size(
        self, source: Path, regions: Optional[SpeakerRegions]
    ) -> Tuple[int, int]:
        if regions and regions.frame_width and regions.frame_height:
            return regions.frame_width, regions.frame_height
        try:
            _dur, w, h = self.ffmpeg.get_video_info(source)
            return w, h
        except Exception:  # noqa: BLE001
            return 1920, 1080

    def _panel_boxes(
        self,
        regions: SpeakerRegions,
        out_w: int,
        half_h: int,
    ) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
        """Crops grandes para cada panel (se adaptan al AR del panel)."""
        sp_a, sp_b = regions.speakers[0], regions.speakers[1]
        top = speaker_panel_crop(
            regions.frame_width, regions.frame_height, sp_a, out_w, half_h, zoom=1.0
        )
        bot = speaker_panel_crop(
            regions.frame_width, regions.frame_height, sp_b, out_w, half_h, zoom=1.0
        )
        logger.info("Interview panels top=%s bot=%s (src %dx%d)", top, bot, regions.frame_width, regions.frame_height)
        return top, bot

    def _render_interview_stack(
        self,
        source: Path,
        output: Path,
        *,
        start: float,
        end: float,
        out_w: int,
        out_h: int,
        options: ProcessOptions,
        regions: Optional[SpeakerRegions],
        activity: Optional[Sequence[ActiveSegment]],
    ) -> Path:
        if regions is None or len(regions.speakers) < 2:
            try:
                regions, detected_activity = self.face_tracker.analyze_video(
                    source,
                    start=start,
                    end=end,
                    max_speakers=2,
                    sample_every_sec=1.0,
                    max_samples=24,
                )
                if not activity:
                    activity = detected_activity
            except Exception as exc:  # noqa: BLE001
                logger.warning("Fallback a reformat simple: %s", exc)
                return self.ffmpeg.cut_and_reformat(
                    source, output, start=start, end=end,
                    out_w=out_w, out_h=out_h, fill_mode=options.fill_mode.value,
                    mirror_horizontal=options.mirror_horizontal,
                )

        if len(regions.speakers) < 2:
            face = regions.primary
            src_w, src_h = regions.frame_width, regions.frame_height
            focus = None
            if face:
                focus = compute_cover_crop(
                    src_w, src_h, out_w, out_h, face.cx, face.cy, contain=face
                )
            return self.ffmpeg.cut_and_reformat(
                source, output, start=start, end=end,
                out_w=out_w, out_h=out_h, fill_mode=options.fill_mode.value,
                focus_box=focus, src_size=(src_w, src_h),
                mirror_horizontal=options.mirror_horizontal,
            )

        half_h = out_h // 2
        top_box, bottom_box = self._panel_boxes(regions, out_w, half_h)
        clip_activity = self._clip_activity(activity or [], start, end)

        if (
            options.interview_layout == InterviewLayout.ACTIVE_FOCUS
            and len(clip_activity) > 1
        ):
            return self._render_dynamic_stack(
                source, output,
                start=start, end=end,
                out_w=out_w, half_h=half_h,
                top_box=top_box, bottom_box=bottom_box,
                activity=clip_activity,
                swap_boxes=(bottom_box, top_box),
                mirror_horizontal=options.mirror_horizontal,
            )

        return self.ffmpeg.cut_interview_stack(
            source, output,
            start=start, end=end,
            out_w=out_w, half_h=half_h,
            top_box=top_box, bottom_box=bottom_box,
            mirror_horizontal=options.mirror_horizontal,
        )

    def _render_dynamic_stack(
        self,
        source: Path,
        output: Path,
        *,
        start: float,
        end: float,
        out_w: int,
        half_h: int,
        top_box: Tuple[int, int, int, int],
        bottom_box: Tuple[int, int, int, int],
        activity: Sequence[ActiveSegment],
        swap_boxes: Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]],
        mirror_horizontal: bool = False,
    ) -> Path:
        tmp_dir = output.parent / f"_dyn_{output.stem}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        parts: List[Path] = []
        swapped_top, swapped_bot = swap_boxes

        for i, seg in enumerate(activity):
            if seg.end <= seg.start:
                continue
            part = tmp_dir / f"part_{i:03d}.mp4"
            if seg.speaker_idx == 0:
                t_box, b_box = top_box, bottom_box
            else:
                t_box, b_box = swapped_top, swapped_bot
            self.ffmpeg.cut_interview_stack(
                source, part,
                start=start + seg.start, end=start + seg.end,
                out_w=out_w, half_h=half_h,
                top_box=t_box, bottom_box=b_box,
                mirror_horizontal=mirror_horizontal,
            )
            parts.append(part)

        if not parts:
            return self.ffmpeg.cut_interview_stack(
                source, output, start=start, end=end,
                out_w=out_w, half_h=half_h,
                top_box=top_box, bottom_box=bottom_box,
                mirror_horizontal=mirror_horizontal,
            )

        if len(parts) == 1:
            parts[0].replace(output)
        else:
            self.ffmpeg.concat_clips(parts, output)

        for p in parts:
            if p.exists() and p != output:
                p.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass
        return output

    @staticmethod
    def _clip_activity(
        activity: Sequence[ActiveSegment],
        clip_start: float,
        clip_end: float,
    ) -> List[ActiveSegment]:
        result: List[ActiveSegment] = []
        for seg in activity:
            s = max(seg.start, clip_start)
            e = min(seg.end, clip_end)
            if e - s < 0.15:
                continue
            result.append(
                ActiveSegment(
                    start=s - clip_start,
                    end=e - clip_start,
                    speaker_idx=seg.speaker_idx,
                )
            )
        if not result:
            result.append(ActiveSegment(0.0, clip_end - clip_start, 0))
        return result
