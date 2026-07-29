import { useCallback, useRef, useState } from 'react'
import type { CropBoxNorm } from '../../api/compose'

interface CropEditorProps {
  videoUrl: string
  top: CropBoxNorm
  bottom: CropBoxNorm
  active: 'top' | 'bottom'
  panelAspect: number
  onChangeTop: (b: CropBoxNorm) => void
  onChangeBottom: (b: CropBoxNorm) => void
  onActiveChange: (a: 'top' | 'bottom') => void
  onTimeUpdate?: (t: number) => void
  onDuration?: (d: number) => void
}

function clampBox(box: CropBoxNorm): CropBoxNorm {
  const w = Math.min(1, Math.max(0.08, box.w))
  const h = Math.min(1, Math.max(0.08, box.h))
  const x = Math.min(1 - w, Math.max(0, box.x))
  const y = Math.min(1 - h, Math.max(0, box.y))
  return { x, y, w, h }
}

function fitAspect(box: CropBoxNorm, panelAr: number, frameAr: number): CropBoxNorm {
  const target = panelAr / Math.max(frameAr, 0.01)
  const cx = box.x + box.w / 2
  const cy = box.y + box.h / 2
  let w = box.w
  let h = box.h
  const current = w / Math.max(h, 0.001)
  if (current > target) w = h * target
  else h = w / target
  if (w > 1) {
    w = 1
    h = w / target
  }
  if (h > 1) {
    h = 1
    w = h * target
  }
  return clampBox({ x: cx - w / 2, y: cy - h / 2, w, h })
}

export function CropEditor({
  videoUrl,
  top,
  bottom,
  active,
  panelAspect,
  onChangeTop,
  onChangeBottom,
  onActiveChange,
  onTimeUpdate,
  onDuration,
}: CropEditorProps) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [frameAr, setFrameAr] = useState(16 / 9)
  const drag = useRef<{
    mode: 'move' | 'resize'
    startX: number
    startY: number
    orig: CropBoxNorm
  } | null>(null)

  const setActiveBox = useCallback(
    (next: CropBoxNorm) => {
      const fitted = fitAspect(next, panelAspect, frameAr)
      if (active === 'top') onChangeTop(fitted)
      else onChangeBottom(fitted)
    },
    [active, frameAr, onChangeBottom, onChangeTop, panelAspect],
  )

  const onPointerDown = (e: React.PointerEvent, mode: 'move' | 'resize') => {
    e.preventDefault()
    e.stopPropagation()
    const box = active === 'top' ? top : bottom
    drag.current = {
      mode,
      startX: e.clientX,
      startY: e.clientY,
      orig: { ...box },
    }
    ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current || !wrapRef.current) return
    const rect = wrapRef.current.getBoundingClientRect()
    const dx = (e.clientX - drag.current.startX) / rect.width
    const dy = (e.clientY - drag.current.startY) / rect.height
    const o = drag.current.orig
    if (drag.current.mode === 'move') {
      setActiveBox({ ...o, x: o.x + dx, y: o.y + dy })
    } else {
      setActiveBox({ ...o, w: o.w + dx, h: o.h + dy })
    }
  }

  const onPointerUp = () => {
    drag.current = null
  }

  const renderBox = (box: CropBoxNorm, kind: 'top' | 'bottom') => {
    const isActive = active === kind
    const color = kind === 'top' ? '#22d3ee' : '#fbbf24'
    return (
      <div
        key={kind}
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation()
          onActiveChange(kind)
        }}
        onPointerDown={(e) => {
          onActiveChange(kind)
          onPointerDown(e, 'move')
        }}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        className="absolute cursor-move"
        style={{
          left: `${box.x * 100}%`,
          top: `${box.y * 100}%`,
          width: `${box.w * 100}%`,
          height: `${box.h * 100}%`,
          border: `2px solid ${color}`,
          backgroundColor: isActive ? `${color}22` : `${color}11`,
          zIndex: isActive ? 20 : 10,
        }}
      >
        <span
          className="absolute left-1 top-1 rounded px-1.5 py-0.5 text-[10px] font-semibold text-black"
          style={{ background: color }}
        >
          {kind === 'top' ? 'ARRIBA' : 'ABAJO'}
        </span>
        {isActive && (
          <div
            className="absolute bottom-0 right-0 h-4 w-4 cursor-se-resize rounded-tl bg-white"
            onPointerDown={(e) => onPointerDown(e, 'resize')}
          />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div
        ref={wrapRef}
        className="relative overflow-hidden rounded-xl border border-white/10 bg-black"
      >
        <video
          src={videoUrl}
          className="block max-h-[420px] w-full object-contain"
          controls
          playsInline
          onLoadedMetadata={(e) => {
            const v = e.currentTarget
            if (v.videoWidth && v.videoHeight) {
              setFrameAr(v.videoWidth / v.videoHeight)
            }
            onDuration?.(v.duration || 0)
          }}
          onTimeUpdate={(e) => onTimeUpdate?.(e.currentTarget.currentTime)}
        />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          {/* overlay alineado al object-contain: aproximamos con el mismo contenedor */}
          <div className="pointer-events-auto absolute inset-0">
            {renderBox(top, 'top')}
            {renderBox(bottom, 'bottom')}
          </div>
        </div>
      </div>
      <p className="text-[11px] text-slate-500">
        Reproduce el video, arrastra los cuadros y redimensiona por la esquina. Cian = arriba ·
        Ámbar = abajo.
      </p>
    </div>
  )
}
