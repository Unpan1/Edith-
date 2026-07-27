import type { Clip } from '../types'
import { clipDownloadUrl, clipThumbnailUrl } from '../api/client'
import { formatDuration } from '../utils/format'

interface ClipCardProps {
  clip: Clip
  onPlay: () => void
}

function aspectClass(formato: string | null): string {
  if (!formato) return 'aspect-video'
  if (formato.includes('vertical') || formato.includes('portrait')) {
    return 'aspect-[9/16] max-h-72 mx-auto w-full max-w-[200px]'
  }
  if (formato === 'square_1_1') return 'aspect-square'
  return 'aspect-video'
}

export function ClipCard({ clip, onPlay }: ClipCardProps) {
  return (
    <article className="group overflow-hidden rounded-xl border border-white/8 bg-white/[0.03] transition hover:border-cyan-400/30 hover:bg-white/[0.05]">
      <div className={`relative overflow-hidden bg-[#12151e] ${aspectClass(clip.formato)}`}>
        <img
          src={clipThumbnailUrl(clip.id)}
          alt={clip.titulo_generado ?? `Clip ${clip.id}`}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          onError={(e) => {
            ;(e.target as HTMLImageElement).style.display = 'none'
          }}
        />
        <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition group-hover:bg-black/40 group-hover:opacity-100">
          <button
            type="button"
            onClick={onPlay}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-cyan-400 text-[#0a0c10] shadow-lg shadow-cyan-500/30"
            aria-label="Reproducir"
          >
            <svg className="ml-0.5 h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </button>
        </div>
        <span className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 font-mono text-[10px] text-white">
          {formatDuration(clip.duracion)}
        </span>
        <span className="absolute top-2 left-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-cyan-300">
          score {clip.score.toFixed(1)}
        </span>
        {clip.formato && (
          <span className="absolute top-2 right-2 max-w-[45%] truncate rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-teal-300">
            {clip.formato.replace(/_/g, ' ')}
          </span>
        )}
      </div>
      <div className="space-y-3 p-3">
        <h3 className="line-clamp-2 text-sm font-medium leading-snug text-white">
          {clip.titulo_generado || `Clip #${clip.id}`}
        </h3>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onPlay}
            className="flex-1 rounded-lg border border-white/10 py-1.5 text-xs text-slate-300 transition hover:border-cyan-400/40 hover:text-cyan-300"
          >
            Reproducir
          </button>
          <a
            href={clipDownloadUrl(clip.id)}
            download
            className="flex-1 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 py-1.5 text-center text-xs font-medium text-[#0a0c10] transition hover:brightness-110"
          >
            Descargar
          </a>
        </div>
      </div>
    </article>
  )
}
