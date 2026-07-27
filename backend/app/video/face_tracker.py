"""Detección y seguimiento de rostros con OpenCV (local)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)

ProgressCb = Callable[[str], None]


@dataclass
class FaceBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def area(self) -> int:
        return self.w * self.h

    def expand(self, frame_w: int, frame_h: int, pad: float = 0.55) -> "FaceBox":
        """Expande el box para incluir hombros / cabeza (recorte vertical)."""
        nw = int(self.w * (1 + pad * 1.2))
        nh = int(self.h * (1 + pad * 2.2))
        cx, cy = int(self.cx), int(self.cy - self.h * 0.15)
        x = max(0, cx - nw // 2)
        y = max(0, cy - nh // 2)
        if x + nw > frame_w:
            x = max(0, frame_w - nw)
        if y + nh > frame_h:
            y = max(0, frame_h - nh)
        nw = min(nw, frame_w - x)
        nh = min(nh, frame_h - y)
        return FaceBox(x, y, nw, nh)

    def as_crop_tuple(self) -> Tuple[int, int, int, int]:
        """(x, y, w, h) para FFmpeg crop."""
        return self.x, self.y, self.w, self.h


@dataclass
class SpeakerRegions:
    """Hasta dos hablantes ordenados izquierda → derecha (o único)."""

    speakers: List[FaceBox]
    frame_width: int
    frame_height: int

    @property
    def primary(self) -> Optional[FaceBox]:
        return self.speakers[0] if self.speakers else None


@dataclass
class ActiveSegment:
    """Intervalo donde un hablante está activo (índice 0 o 1)."""

    start: float
    end: float
    speaker_idx: int


class FaceTracker:
    """Detecta rostros y estima quién habla por movimiento facial."""

    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)
        if self._cascade.empty():
            logger.warning("No se pudo cargar Haar cascade de rostros")

    def detect_faces(self, frame: np.ndarray) -> List[FaceBox]:
        # Reducir resolución acelera Haar mucho en videos 1080p/4K
        h, w = frame.shape[:2]
        scale = 1.0
        work = frame
        if max(h, w) > 960:
            scale = 960 / max(h, w)
            work = cv2.resize(frame, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        detections = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(40, 40),
        )
        inv = 1.0 / scale
        faces = [
            FaceBox(int(x * inv), int(y * inv), int(fw * inv), int(fh * inv))
            for x, y, fw, fh in detections
        ]
        faces.sort(key=lambda f: f.area, reverse=True)
        return faces

    def analyze_video(
        self,
        video_path: str | Path,
        *,
        sample_every_sec: float = 0.75,
        max_speakers: int = 2,
        start: float = 0.0,
        end: Optional[float] = None,
        max_samples: int = 48,
        on_progress: Optional[ProgressCb] = None,
    ) -> Tuple[SpeakerRegions, List[ActiveSegment]]:
        """
        Muestrea el video (con tope de muestras), agrupa rostros
        y genera timeline de hablante activo por movimiento.
        """
        t0 = time.perf_counter()
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"No se pudo abrir video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = total_frames / fps if fps > 0 else 0.0
        end = min(end or duration, duration)
        span = max(0.1, end - max(0.0, start))

        # Adaptar intervalo para no pasar de max_samples
        max_samples = max(6, int(max_samples))
        adaptive = max(sample_every_sec, span / max_samples)
        sample_times = []
        t = max(0.0, start)
        while t <= end + 1e-6 and len(sample_times) < max_samples:
            sample_times.append(t)
            t += adaptive

        if on_progress:
            on_progress(
                f"Detectando rostros ({len(sample_times)} muestras en {span:.0f}s de video)…"
            )

        logger.info(
            "FaceTracker: %.1fs video → %d muestras (cada %.2fs, max=%d, speakers=%d)",
            span,
            len(sample_times),
            adaptive,
            max_samples,
            max_speakers,
        )

        # Solo guardamos caras + ROI pequeño (no el frame completo)
        samples: List[Tuple[float, List[FaceBox], Optional[np.ndarray]]] = []
        need_motion = max_speakers >= 2

        for i, ts in enumerate(sample_times):
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ok, frame = cap.read()
            if not ok:
                break
            faces = self.detect_faces(frame)[:max_speakers]
            # Guardar frame reducido solo si hace falta timeline de actividad
            small = None
            if need_motion:
                small = cv2.resize(frame, (320, int(320 * height / max(width, 1))))
            samples.append((ts, faces, small))
            if on_progress and i > 0 and i % 8 == 0:
                on_progress(f"Rostros: muestra {i + 1}/{len(sample_times)}…")

        cap.release()

        if not samples:
            return SpeakerRegions([], width, height), []

        all_faces = [f for _, faces, _ in samples for f in faces]
        if not all_faces:
            box = FaceBox(width // 4, height // 8, width // 2, int(height * 0.75))
            logger.info("FaceTracker: sin rostros (%.2fs)", time.perf_counter() - t0)
            return SpeakerRegions([box], width, height), [
                ActiveSegment(start, end, 0)
            ]

        xs = sorted(f.cx for f in all_faces)
        if len(xs) == 1 or max_speakers == 1 or (xs[-1] - xs[0]) < width * 0.15:
            avg = self._average_face(all_faces, width, height)
            logger.info(
                "FaceTracker: 1 hablante en %.2fs",
                time.perf_counter() - t0,
            )
            return SpeakerRegions([avg], width, height), [
                ActiveSegment(start, end, 0)
            ]

        mid_x = (xs[0] + xs[-1]) / 2
        left_faces = [f for f in all_faces if f.cx <= mid_x]
        right_faces = [f for f in all_faces if f.cx > mid_x]
        if not left_faces:
            left_faces = all_faces[: len(all_faces) // 2 or 1]
        if not right_faces:
            right_faces = all_faces[len(all_faces) // 2 :]

        speaker_boxes = [
            self._average_face(left_faces, width, height).expand(width, height),
            self._average_face(right_faces, width, height).expand(width, height),
        ]

        # Escalar boxes al frame reducido (320px ancho)
        sx = 320 / max(width, 1)
        sy = (320 * height / max(width, 1)) / max(height, 1)
        small_boxes = [
            FaceBox(
                int(b.x * sx),
                int(b.y * sy),
                max(1, int(b.w * sx)),
                max(1, int(b.h * sy)),
            )
            for b in speaker_boxes
        ]

        active_timeline: List[ActiveSegment] = []
        prev_gray_rois: List[Optional[np.ndarray]] = [None, None]
        current_speaker = 0
        seg_start = start

        for ts, faces, frame in samples:
            if frame is None:
                continue
            scores = []
            for idx, box in enumerate(small_boxes):
                y2 = min(frame.shape[0], box.y + box.h)
                x2 = min(frame.shape[1], box.x + box.w)
                roi = frame[box.y : y2, box.x : x2]
                if roi.size == 0:
                    scores.append(0.0)
                    continue
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (48, 48))
                motion = 0.0
                if prev_gray_rois[idx] is not None:
                    diff = cv2.absdiff(gray, prev_gray_rois[idx])
                    motion = float(np.mean(diff))
                prev_gray_rois[idx] = gray
                face_bonus = 0.0
                for f in faces:
                    if abs(f.cx - speaker_boxes[idx].cx) < speaker_boxes[idx].w * 0.6:
                        face_bonus = 8.0
                        break
                scores.append(motion + face_bonus)

            winner = int(np.argmax(scores)) if scores else 0
            if scores and scores[winner] < 3.0:
                winner = current_speaker

            if winner != current_speaker:
                if ts - seg_start >= 0.4:
                    active_timeline.append(ActiveSegment(seg_start, ts, current_speaker))
                    seg_start = ts
                    current_speaker = winner

        active_timeline.append(ActiveSegment(seg_start, end, current_speaker))
        active_timeline = self._merge_short(active_timeline, min_len=0.8)

        regions = SpeakerRegions(speaker_boxes, width, height)
        logger.info(
            "FaceTracker: %d hablantes | %d segs timeline | %.2fs",
            len(speaker_boxes),
            len(active_timeline),
            time.perf_counter() - t0,
        )
        return regions, active_timeline

    @staticmethod
    def _average_face(faces: Sequence[FaceBox], fw: int, fh: int) -> FaceBox:
        x = int(sum(f.x for f in faces) / len(faces))
        y = int(sum(f.y for f in faces) / len(faces))
        w = int(sum(f.w for f in faces) / len(faces))
        h = int(sum(f.h for f in faces) / len(faces))
        return FaceBox(x, y, max(1, w), max(1, h))

    @staticmethod
    def _merge_short(segments: List[ActiveSegment], min_len: float) -> List[ActiveSegment]:
        if not segments:
            return []
        merged = [segments[0]]
        for seg in segments[1:]:
            prev = merged[-1]
            if seg.speaker_idx == prev.speaker_idx or (seg.end - seg.start) < min_len:
                merged[-1] = ActiveSegment(prev.start, seg.end, prev.speaker_idx)
            else:
                merged.append(seg)
        return merged
