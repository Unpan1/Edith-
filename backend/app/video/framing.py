"""Cálculo de recortes que se adaptan al formato sin destruir calidad.

Principio: usar el mayor recorte posible del video fuente con el aspect ratio
de salida, centrado en el sujeto. Así se escala hacia abajo (o 1:1), nunca
se hace zoom extremo a un rostro pequeño (pixelación).
"""

from __future__ import annotations

from typing import Optional, Tuple

from app.video.face_tracker import FaceBox


def compute_cover_crop(
    src_w: int,
    src_h: int,
    out_w: int,
    out_h: int,
    focus_cx: float,
    focus_cy: float,
    *,
    contain: Optional[FaceBox] = None,
    zoom: float = 1.0,
) -> Tuple[int, int, int, int]:
    """
    Recorte máximo (alejado) con el mismo aspect ratio que la salida.

    - zoom=1.0 → máximo alejamiento (mejor calidad)
    - zoom>1   → más cerca del sujeto (máx ~2.5)
    - contain  → el crop incluye al menos este box (cara + hombros)

    Retorna (x, y, w, h) en coordenadas del video fuente.
    """
    if src_w <= 0 or src_h <= 0 or out_w <= 0 or out_h <= 0:
        return 0, 0, max(2, src_w), max(2, src_h)

    target_ar = out_w / out_h
    zoom = max(1.0, min(float(zoom), 2.5))

    # Crop máximo que cabe en el fuente con ese AR
    if src_w / src_h > target_ar:
        max_h = src_h
        max_w = int(round(max_h * target_ar))
    else:
        max_w = src_w
        max_h = int(round(max_w / target_ar))

    crop_w = int(round(max_w / zoom))
    crop_h = int(round(max_h / zoom))

    # Asegurar que quepa la cara (con margen) si se pidió
    if contain is not None and contain.w > 0 and contain.h > 0:
        # Margen generoso alrededor de la cara (hombros / cabeza)
        need_w = int(contain.w * 2.4)
        need_h = int(contain.h * 3.2)
        # Ajustar al AR de salida
        if need_w / need_h > target_ar:
            need_h = int(round(need_w / target_ar))
        else:
            need_w = int(round(need_h * target_ar))
        crop_w = max(crop_w, min(need_w, max_w))
        crop_h = max(crop_h, min(need_h, max_h))
        # Re-sincronizar AR
        if crop_w / crop_h > target_ar:
            crop_h = int(round(crop_w / target_ar))
        else:
            crop_w = int(round(crop_h * target_ar))
        crop_w = min(crop_w, max_w, src_w)
        crop_h = min(crop_h, max_h, src_h)

    crop_w = max(2, crop_w - crop_w % 2)
    crop_h = max(2, crop_h - crop_h % 2)
    crop_w = min(crop_w, src_w - src_w % 2)
    crop_h = min(crop_h, src_h - src_h % 2)

    # Preferir un poco de headroom (cara un poco arriba del centro)
    prefer_cy = focus_cy - crop_h * 0.08

    x = int(round(focus_cx - crop_w / 2))
    y = int(round(prefer_cy - crop_h / 2))
    x = max(0, min(x, src_w - crop_w))
    y = max(0, min(y, src_h - crop_h))

    # Si hay contain, intentar incluirlo desplazando el crop
    if contain is not None:
        pad = int(max(contain.w, contain.h) * 0.35)
        left = contain.x - pad
        right = contain.x + contain.w + pad
        top = contain.y - pad
        bottom = contain.y + contain.h + pad
        if left < x:
            x = max(0, left)
        if right > x + crop_w:
            x = min(src_w - crop_w, right - crop_w)
        if top < y:
            y = max(0, top)
        if bottom > y + crop_h:
            y = min(src_h - crop_h, bottom - crop_h)
        x = max(0, min(x, src_w - crop_w))
        y = max(0, min(y, src_h - crop_h))

    return x, y, crop_w, crop_h


def speaker_panel_crop(
    src_w: int,
    src_h: int,
    face: FaceBox,
    panel_w: int,
    panel_h: int,
    *,
    zoom: float = 1.0,
) -> Tuple[int, int, int, int]:
    """Recorte para un panel de entrevista (mitad superior/inferior)."""
    # Centro un poco más arriba (incluir cabeza, no solo mentón)
    cy = face.cy - face.h * 0.2
    return compute_cover_crop(
        src_w,
        src_h,
        panel_w,
        panel_h,
        face.cx,
        cy,
        contain=face,
        zoom=zoom,
    )
