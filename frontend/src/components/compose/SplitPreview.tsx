import { useEffect, useRef } from 'react'
import type { CropBoxNorm } from '../../api/compose'
import type { ClipFormat } from '../../types'
import { FORMAT_LABELS } from '../../types'

const ASPECT: Record<ClipFormat, string> = {
  vertical_9_16: '9 / 16',
  portrait_4_5: '4 / 5',
  square_1_1: '1 / 1',
  landscape_16_9: '16 / 9',
}

interface SplitPreviewProps {
  videoUrl: string
  format: ClipFormat
  top: CropBoxNorm
  bottom: CropBoxNorm
  currentTime?: number
}

export function SplitPreview({ videoUrl, format, top, bottom, currentTime }: SplitPreviewProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Vista previa</span>
        <span className="text-slate-400">{FORMAT_LABELS[format].split('·')[0].trim()}</span>
      </div>
      <div
        className="mx-auto overflow-hidden rounded-xl border border-white/15 bg-black shadow-xl"
        style={{ aspectRatio: ASPECT[format], width: '100%', maxWidth: 260 }}
      >
        <CroppedPanel videoUrl={videoUrl} box={top} label="Arriba" tint="cyan" currentTime={currentTime} />
        <CroppedPanel videoUrl={videoUrl} box={bottom} label="Abajo" tint="amber" currentTime={currentTime} />
      </div>
    </div>
  )
}

function CroppedPanel({
  videoUrl,
  box,
  label,
  tint,
  currentTime,
}: {
  videoUrl: string
  box: CropBoxNorm
  label: string
  tint: 'cyan' | 'amber'
  currentTime?: number
}) {
  const ref = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el || currentTime == null) return
    if (Math.abs(el.currentTime - currentTime) > 0.35) {
      el.currentTime = currentTime
    }
  }, [currentTime])

  const w = Math.max(box.w, 0.05)
  const h = Math.max(box.h, 0.05)

  return (
    <div className="relative h-1/2 w-full overflow-hidden border-b border-white/10 last:border-0">
      <div
        className="absolute"
        style={{
          width: `${(1 / w) * 100}%`,
          height: `${(1 / h) * 100}%`,
          left: `${(-box.x / w) * 100}%`,
          top: `${(-box.y / h) * 100}%`,
        }}
      >
        <video
          ref={ref}
          src={videoUrl}
          muted
          playsInline
          className="h-full w-full object-cover"
        />
      </div>
      <span
        className={[
          'absolute left-1.5 top-1.5 z-10 rounded px-1.5 py-0.5 text-[9px] font-semibold',
          tint === 'cyan' ? 'bg-cyan-400 text-black' : 'bg-amber-400 text-black',
        ].join(' ')}
      >
        {label}
      </span>
    </div>
  )
}
