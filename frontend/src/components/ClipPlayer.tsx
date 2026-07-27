import { useEffect, useRef } from 'react'
import { clipStreamUrl } from '../api/client'
import type { Clip } from '../types'
import { formatDuration } from '../utils/format'

interface ClipPlayerProps {
  clip: Clip
  onClose: () => void
}

export function ClipPlayer({ clip, onClose }: ClipPlayerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 m-0 flex h-full w-full max-w-none items-center justify-center bg-black/80 p-4 backdrop:bg-black/80"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose()
      }}
    >
      <div className="w-full max-w-3xl overflow-hidden rounded-2xl border border-white/10 bg-[#12151e] shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
          <div>
            <h2 className="text-sm font-medium text-white">
              {clip.titulo_generado || `Clip #${clip.id}`}
            </h2>
            <p className="text-xs text-slate-500">
              {formatDuration(clip.duracion)} · {clip.inicio.toFixed(1)}s – {clip.fin.toFixed(1)}s
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-white/5 hover:text-white"
            aria-label="Cerrar"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <video
          key={clip.id}
          src={clipStreamUrl(clip.id)}
          controls
          autoPlay
          className="aspect-video w-full bg-black"
        />
      </div>
    </dialog>
  )
}
