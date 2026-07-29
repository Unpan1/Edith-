"""Diarización de hablantes local (sin API de pago) con features de audio + k-means."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _load_mono_wav(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(n)
    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    elif sw == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float32)
    else:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    peak = np.max(np.abs(data)) + 1e-9
    data = data / peak
    return data, sr


def _segment_features(audio: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    """Vector compacto: energía, zcr, centroide espectral, rolloff aprox."""
    i0 = max(0, int(start * sr))
    i1 = min(len(audio), int(end * sr))
    if i1 - i0 < sr * 0.08:
        # demasiado corto: pad con silencio
        chunk = np.zeros(max(1, int(sr * 0.12)), dtype=np.float32)
        chunk[: max(0, i1 - i0)] = audio[i0:i1]
    else:
        chunk = audio[i0:i1]

    # Limitar longitud para FFT rápido
    max_samples = int(sr * 2.5)
    if len(chunk) > max_samples:
        chunk = chunk[:max_samples]

    energy = float(np.sqrt(np.mean(chunk ** 2) + 1e-12))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(chunk).astype(np.float32)))))

    # Espectro
    win = np.hanning(len(chunk))
    spec = np.abs(np.fft.rfft(chunk * win)) + 1e-12
    freqs = np.fft.rfftfreq(len(chunk), d=1.0 / sr)
    centroid = float(np.sum(freqs * spec) / np.sum(spec))
    cum = np.cumsum(spec)
    rolloff_idx = int(np.searchsorted(cum, 0.85 * cum[-1]))
    rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])
    # Banda baja / alta (voz)
    mid = len(spec) // 4
    low = float(np.mean(spec[:mid]))
    high = float(np.mean(spec[mid:]))
    return np.array([energy, zcr, centroid / 5000.0, rolloff / 8000.0, low, high], dtype=np.float32)


def _kmeans_2(x: np.ndarray, max_iter: int = 25) -> Tuple[np.ndarray, float]:
    """K-means 2 clusters. Retorna labels 0/1 y separación relativa."""
    if len(x) < 4:
        return np.zeros(len(x), dtype=np.int32), 0.0

    # init: extremos por energía (col 0) o primer/último
    order = np.argsort(x[:, 0])
    c0 = x[order[0]].copy()
    c1 = x[order[-1]].copy()
    labels = np.zeros(len(x), dtype=np.int32)

    for _ in range(max_iter):
        d0 = np.linalg.norm(x - c0, axis=1)
        d1 = np.linalg.norm(x - c1, axis=1)
        new_labels = (d1 < d0).astype(np.int32)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        if np.any(labels == 0):
            c0 = x[labels == 0].mean(axis=0)
        if np.any(labels == 1):
            c1 = x[labels == 1].mean(axis=0)

    # Separación: distancia entre centros / dispersión
    sep = float(np.linalg.norm(c0 - c1))
    spread = float(np.mean(np.linalg.norm(x - x.mean(axis=0), axis=1)) + 1e-9)
    score = sep / spread
    return labels, score


def assign_speakers(
    audio_path: Path,
    segments: Sequence[Tuple[float, float]],
    *,
    max_speakers: int = 2,
    min_separation: float = 0.85,
) -> Tuple[List[int], int]:
    """
    Asigna speaker_id (1-based) a cada segmento.
    Retorna (lista de ids, número de hablantes detectados).
    """
    if not segments:
        return [], 1

    try:
        audio, sr = _load_mono_wav(Path(audio_path))
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer audio para diarización: %s", exc)
        return [1] * len(segments), 1

    feats = []
    for start, end in segments:
        feats.append(_segment_features(audio, sr, start, end))
    x = np.stack(feats, axis=0)
    # Normalizar columnas
    std = x.std(axis=0) + 1e-9
    x = (x - x.mean(axis=0)) / std

    if max_speakers < 2 or len(segments) < 4:
        return [1] * len(segments), 1

    labels, score = _kmeans_2(x)
    # Suavizar: si un segmento aislado cambia de hablante < 0.4s, heredar vecinos
    labels = _smooth_labels(labels, segments)

    n0 = int(np.sum(labels == 0))
    n1 = int(np.sum(labels == 1))
    # Si un cluster es casi vacío o separación débil → un solo hablante
    if score < min_separation or min(n0, n1) < max(2, len(segments) * 0.08):
        logger.info("Diarización: 1 hablante (score=%.2f)", score)
        return [1] * len(segments), 1

    # Mapear a 1,2 con el que habla primero = 1
    first = int(labels[0])
    mapping = {first: 1, 1 - first: 2}
    speakers = [mapping[int(l)] for l in labels]
    logger.info(
        "Diarización: 2 hablantes (score=%.2f, dist=%d/%d)",
        score,
        n0,
        n1,
    )
    return speakers, 2


def _smooth_labels(
    labels: np.ndarray, segments: Sequence[Tuple[float, float]]
) -> np.ndarray:
    out = labels.copy()
    for i in range(1, len(out) - 1):
        if out[i] != out[i - 1] and out[i] != out[i + 1]:
            # flip corto
            dur = segments[i][1] - segments[i][0]
            if dur < 0.55:
                out[i] = out[i - 1]
    # Tras pausa larga, permitir cambio; tras pausa corta, preferir continuidad
    for i in range(1, len(out)):
        gap = segments[i][0] - segments[i - 1][1]
        if gap < 0.35 and out[i] != out[i - 1]:
            # cambio sospechoso sin pausa
            out[i] = out[i - 1]
    return out


def format_dialogue(
    texts: Sequence[str],
    speakers: Sequence[int],
    *,
    starts: Optional[Sequence[float]] = None,
) -> str:
    """Une turnos consecutivos del mismo hablante."""
    if not texts:
        return ""
    lines: List[str] = []
    cur_sp = speakers[0] if speakers else 1
    buf: List[str] = []

    def flush() -> None:
        nonlocal buf, cur_sp
        if not buf:
            return
        body = " ".join(t.strip() for t in buf if t.strip()).strip()
        if body:
            lines.append(f"[Hablante {cur_sp}]: {body}")
        buf = []

    for i, text in enumerate(texts):
        sp = speakers[i] if i < len(speakers) else 1
        if sp != cur_sp:
            flush()
            cur_sp = sp
        buf.append(text)
    flush()
    return "\n\n".join(lines)
