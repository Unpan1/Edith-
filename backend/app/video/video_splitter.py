"""Divide el video completo en partes consecutivas (sin detección de highlights)."""

from __future__ import annotations

import math
from typing import List

from app.ai.highlight_detector import HighlightCandidate
from app.schemas.options import ProcessOptions, ProcessingMode, SplitStrategy


def build_full_video_segments(
    duration: float,
    options: ProcessOptions,
) -> List[HighlightCandidate]:
    """
    Genera segmentos consecutivos que cubren todo el video.
    Compatible con ClipService (HighlightCandidate).
    """
    if duration <= 0.1:
        return []

    min_len = max(3.0, options.min_clip_duration * 0.25)
    parts: List[HighlightCandidate] = []

    if options.split_strategy == SplitStrategy.BY_COUNT:
        n = max(1, min(options.split_part_count, 50))
        step = duration / n
        for i in range(n):
            start = round(i * step, 3)
            end = round(duration if i == n - 1 else (i + 1) * step, 3)
            if end - start < min_len:
                continue
            parts.append(_part_candidate(i + 1, n, start, end))
    else:
        seg = max(min_len, options.split_part_duration)
        n = max(1, math.ceil(duration / seg))
        for i in range(n):
            start = round(i * seg, 3)
            end = round(min(duration, (i + 1) * seg), 3)
            if end - start < min_len:
                break
            parts.append(_part_candidate(i + 1, n, start, end))

    return parts


def _part_candidate(index: int, total: int, start: float, end: float) -> HighlightCandidate:
    dur = max(0.1, end - start)
    # score alto en parte 1 para orden descendente coherente en la UI
    score = round(1000.0 - (index - 1), 2)
    return HighlightCandidate(
        start=start,
        end=end,
        score=score,
        title=f"Parte {index} de {total}",
        segment_indices=[],
        reasons=["full_split"],
    )
