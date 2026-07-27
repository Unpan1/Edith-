"""Generación de subtítulos SRT / VTT / ASS (karaoke) a partir de Whisper."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Sequence

from app.ai.whisper_service import WhisperSegment
from app.schemas.options import SubtitlePosition, SubtitleStyle
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Alineación ASS: 1–3 bottom, 4–6 middle, 7–9 top (numpad)
_ALIGN = {
    SubtitlePosition.BOTTOM: 2,
    SubtitlePosition.CENTER: 5,
    SubtitlePosition.TOP: 8,
}


def resolve_ass_font_size(
    ui_size: int,
    play_h: int,
    style: SubtitleStyle = SubtitleStyle.CLEAN,
) -> int:
    """
    Convierte el tamaño de la UI (12–48) a FontSize ASS relativo a PlayResY.

    En vertical 1080×1920, FontSize=32 es ~1.7% de la altura (ilegible).
    Mapeamos a fracciones típicas de redes (~4–11% de la altura).
    """
    clamped = max(12, min(48, int(ui_size)))
    t = (clamped - 12) / 36.0  # 0..1
    # 12 → 4.2% · 18 → 5.5% · 32 → 8.3% · 48 → 11%
    frac = 0.042 + t * 0.068

    if style in (SubtitleStyle.KARAOKE, SubtitleStyle.SOCIAL):
        frac *= 1.12
    elif style == SubtitleStyle.SUBTLE:
        frac *= 0.72

    size = int(round(max(play_h, 720) * frac))
    return max(36, min(220, size))


class SubtitleService:
    """Crea SRT, VTT y ASS (para estilos interactivos)."""

    def generate_for_clip(
        self,
        segments: Sequence[WhisperSegment] | Sequence[dict],
        clip_start: float,
        clip_end: float,
        output_dir: Path,
        base_name: str,
        *,
        style: SubtitleStyle = SubtitleStyle.CLEAN,
        position: SubtitlePosition = SubtitlePosition.CENTER,
        font_size: int = 18,
        play_res: tuple[int, int] = (1080, 1920),
    ) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """
        Retorna (srt, vtt, ass).
        ass se genera siempre que se vaya a quemar con estilo limpio/karaoke.
        """
        filtered = self._filter_segments(segments, clip_start, clip_end)
        srt_path = output_dir / f"{base_name}.srt"
        vtt_path = output_dir / f"{base_name}.vtt"
        ass_path = output_dir / f"{base_name}.ass"

        self._write_srt(filtered, srt_path, clip_start)
        self._write_vtt(filtered, vtt_path, clip_start)

        words = self._extract_words(segments, clip_start, clip_end)
        self._write_ass(
            filtered,
            words,
            ass_path,
            offset=clip_start,
            style=style,
            position=position,
            font_size=font_size,
            play_res=play_res,
        )

        ass_px = resolve_ass_font_size(font_size, play_res[1], style)
        logger.info(
            "Subtítulos: %s | %s | %s (%d cues, %d words) | UI=%d → ASS=%d @%dx%d",
            srt_path.name,
            vtt_path.name,
            ass_path.name,
            len(filtered),
            len(words),
            font_size,
            ass_px,
            play_res[0],
            play_res[1],
        )
        return srt_path, vtt_path, ass_path

    def _filter_segments(
        self,
        segments: Sequence[WhisperSegment] | Sequence[dict],
        start: float,
        end: float,
    ) -> List[dict]:
        result: List[dict] = []
        for seg in segments:
            if isinstance(seg, WhisperSegment):
                s, e, text = seg.start, seg.end, seg.text
                words = seg.words
            else:
                s = float(seg.get("start", 0))
                e = float(seg.get("end", 0))
                text = str(seg.get("text", "")).strip()
                words = list(seg.get("words") or [])

            if e <= start or s >= end or not text:
                continue

            result.append({
                "start": max(s, start),
                "end": min(e, end),
                "text": text.strip(),
                "words": words,
            })
        return result

    def _extract_words(
        self,
        segments: Sequence[WhisperSegment] | Sequence[dict],
        start: float,
        end: float,
    ) -> List[dict]:
        words: List[dict] = []
        for seg in segments:
            raw_words: List[Any]
            if isinstance(seg, WhisperSegment):
                raw_words = seg.words
            else:
                raw_words = list(seg.get("words") or [])

            for w in raw_words:
                if isinstance(w, dict):
                    ws = float(w.get("start", 0))
                    we = float(w.get("end", ws))
                    text = str(w.get("word") or w.get("text") or "").strip()
                else:
                    continue
                if not text or we <= start or ws >= end:
                    continue
                words.append({
                    "start": max(ws, start),
                    "end": min(we, end),
                    "text": text,
                })

        # Fallback: partir segmentos en palabras sin timing fino
        if not words:
            for cue in self._filter_segments(segments, start, end):
                parts = cue["text"].split()
                if not parts:
                    continue
                dur = max(0.05, cue["end"] - cue["start"])
                step = dur / len(parts)
                for i, p in enumerate(parts):
                    words.append({
                        "start": cue["start"] + i * step,
                        "end": cue["start"] + (i + 1) * step,
                        "text": p,
                    })
        return words

    def _write_ass(
        self,
        cues: List[dict],
        words: List[dict],
        path: Path,
        *,
        offset: float,
        style: SubtitleStyle,
        position: SubtitlePosition,
        font_size: int,
        play_res: tuple[int, int],
    ) -> None:
        pw, ph = play_res
        align = _ALIGN.get(position, 5)
        # Márgenes relativos a la altura del formato
        if position == SubtitlePosition.CENTER:
            margin_v = 0
        elif position == SubtitlePosition.TOP:
            margin_v = max(40, int(ph * 0.06))
        else:
            margin_v = max(60, int(ph * 0.08))

        ass_size = resolve_ass_font_size(font_size, ph, style)
        header = self._ass_header(style, ass_size, align, margin_v, pw, ph)
        events: List[str] = []

        # Tipografía grande → menos palabras por línea
        chunk = 3 if ass_size >= 90 else 4

        if style == SubtitleStyle.KARAOKE and words:
            events = self._karaoke_events(words, offset, chunk_size=chunk)
        elif style == SubtitleStyle.SOCIAL and words:
            events = self._social_chunk_events(words, offset, chunk=chunk)
        else:
            for cue in cues:
                start = self._ass_time(cue["start"] - offset)
                end = self._ass_time(cue["end"] - offset)
                text = self._ass_escape(cue["text"])
                events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    def _ass_header(
        self,
        style: SubtitleStyle,
        font_size: int,
        align: int,
        margin_v: int,
        pw: int,
        ph: int,
    ) -> str:
        # ASS colours: &HAABBGGRR
        # BorderStyle 1 = outline only (SIN caja). 3 = caja opaca.
        # font_size ya viene escalado a PlayResY
        outline_base = max(3.0, font_size * 0.045)

        if style == SubtitleStyle.BOXED:
            border_style = 3
            outline = 0
            shadow = 0
            back = "&H80000000"
            font = "Arial"
            size = font_size
            primary = "&H00FFFFFF"
            secondary = "&H00FFFFFF"
            bold = -1
        elif style == SubtitleStyle.SOCIAL:
            border_style = 1
            outline = outline_base * 1.15
            shadow = max(1.0, font_size * 0.02)
            back = "&H00000000"
            font = "Arial Black"
            size = font_size
            primary = "&H00FFFFFF"
            secondary = "&H0000F0FF"
            bold = -1
        elif style == SubtitleStyle.KARAOKE:
            border_style = 1
            outline = outline_base * 1.2
            shadow = max(1.0, font_size * 0.025)
            back = "&H00000000"
            font = "Arial Black"
            size = font_size
            primary = "&H00FFFFFF"
            secondary = "&H0000E5FF"
            bold = -1
        elif style == SubtitleStyle.SUBTLE:
            border_style = 1
            outline = max(2.0, outline_base * 0.7)
            shadow = 0
            back = "&H00000000"
            font = "Arial"
            size = font_size
            primary = "&H00F0F0F0"
            secondary = primary
            bold = 0
        else:  # CLEAN
            border_style = 1
            outline = outline_base
            shadow = max(0.5, font_size * 0.015)
            back = "&H00000000"
            font = "Arial"
            size = font_size
            primary = "&H00FFFFFF"
            secondary = "&H00FFFFFF"
            bold = -1

        margin_h = max(40, int(pw * 0.06))
        outline_s = f"{outline:.1f}"
        shadow_s = f"{shadow:.1f}"

        style_line = (
            f"Style: Default,{font},{size},{primary},{secondary},"
            f"&H00000000,{back},{bold},0,0,0,100,100,0,0,"
            f"{border_style},{outline_s},{shadow_s},{align},{margin_h},{margin_h},{margin_v},1"
        )

        return (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {pw}\n"
            f"PlayResY: {ph}\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"{style_line}\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def _karaoke_events(
        self, words: List[dict], offset: float, chunk_size: int = 4
    ) -> List[str]:
        """Agrupa palabras en líneas cortas con \\k (centésimas) para resaltado."""
        events: List[str] = []
        for i in range(0, len(words), chunk_size):
            group = words[i : i + chunk_size]
            line_start = group[0]["start"] - offset
            line_end = group[-1]["end"] - offset
            parts: List[str] = []
            for w in group:
                dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                parts.append(f"{{\\k{dur_cs}}}{self._ass_escape(w['text'])}")
            text = " ".join(parts)
            events.append(
                f"Dialogue: 0,{self._ass_time(line_start)},{self._ass_time(line_end)},"
                f"Default,,0,0,0,,{text}"
            )
        return events

    def _social_chunk_events(
        self, words: List[dict], offset: float, chunk: int = 4
    ) -> List[str]:
        """
        Estilo redes: muestra 3–4 palabras; la activa en color highlight
        (un evento por palabra, reescribiendo el grupo).
        """
        events: List[str] = []
        # color ASS BGR: cyan highlight &H0000E5FF, white &H00FFFFFF
        hi = "{\\c&H0000E5FF&\\b1}"
        normal = "{\\c&H00FFFFFF&\\b0}"
        reset = "{\\c&H00FFFFFF&}"

        for i, w in enumerate(words):
            # ventana centrada en la palabra activa
            start_i = max(0, i - 1)
            end_i = min(len(words), start_i + chunk)
            if end_i - start_i < chunk and start_i > 0:
                start_i = max(0, end_i - chunk)
            group = words[start_i:end_i]

            parts: List[str] = []
            for j, gw in enumerate(group):
                global_idx = start_i + j
                token = self._ass_escape(gw["text"])
                if global_idx == i:
                    parts.append(f"{hi}{token}{reset}")
                else:
                    parts.append(f"{normal}{token}")

            line_start = w["start"] - offset
            line_end = w["end"] - offset
            # Evitar cues demasiado cortos
            if line_end - line_start < 0.08:
                line_end = line_start + 0.08
            events.append(
                f"Dialogue: 0,{self._ass_time(line_start)},{self._ass_time(line_end)},"
                f"Default,,0,0,0,,{' '.join(parts)}"
            )
        return events

    def _write_srt(self, cues: List[dict], path: Path, offset: float) -> None:
        lines: List[str] = []
        for i, cue in enumerate(cues, start=1):
            start = self._format_srt_time(cue["start"] - offset)
            end = self._format_srt_time(cue["end"] - offset)
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(cue["text"])
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_vtt(self, cues: List[dict], path: Path, offset: float) -> None:
        lines: List[str] = ["WEBVTT", ""]
        for cue in cues:
            start = self._format_vtt_time(cue["start"] - offset)
            end = self._format_vtt_time(cue["end"] - offset)
            lines.append(f"{start} --> {end}")
            lines.append(cue["text"])
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _ass_escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")

    @staticmethod
    def _ass_time(seconds: float) -> str:
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        if cs == 100:
            s += 1
            cs = 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis == 1000:
            secs += 1
            millis = 0
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis == 1000:
            secs += 1
            millis = 0
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
