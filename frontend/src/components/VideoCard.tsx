import { ACTIVE_STATUSES, STATUS_LABELS, type Video } from '../types'
import { formatDate, formatDuration, formatSize } from '../utils/format'
import { ProgressBar, buildProcessSteps } from './ProgressBar'

interface VideoCardProps {
  video: Video
  selected: boolean
  onSelect: () => void
  onProcess: () => void
  onDelete: () => void
  processing?: boolean
}

export function VideoCard({
  video,
  selected,
  onSelect,
  onProcess,
  onDelete,
  processing,
}: VideoCardProps) {
  const isActive = ACTIVE_STATUSES.includes(video.estado)
  const canProcess =
    video.estado === 'uploaded' || video.estado === 'failed' || video.estado === 'completed'

  return (
    <article
      onClick={onSelect}
      className={[
        'cursor-pointer rounded-xl border p-4 transition-all duration-200',
        selected
          ? 'border-cyan-400/50 bg-cyan-400/8 shadow-lg shadow-cyan-500/5'
          : 'border-white/8 bg-white/[0.03] hover:border-white/15 hover:bg-white/[0.05]',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate font-medium text-white" title={video.nombre_original}>
            {video.nombre_original}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {formatDuration(video.duracion)} · {formatSize(video.tamano)} ·{' '}
            {formatDate(video.fecha_subida)}
          </p>
        </div>
        <StatusBadge status={video.estado} />
      </div>

      {(isActive || video.estado === 'failed') && (
        <div className="mt-3">
          <ProgressBar
            progress={video.progreso}
            status={video.estado}
            detail={video.progreso_detalle}
            etaSeconds={video.eta_segundos}
            steps={isActive ? buildProcessSteps(video.estado) : undefined}
          />
          {video.mensaje_error && (
            <p className="mt-2 line-clamp-2 text-xs text-rose-400">{video.mensaje_error}</p>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
        {canProcess && (
          <button
            type="button"
            disabled={processing || isActive}
            onClick={onProcess}
            className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-3 py-1.5 text-xs font-medium text-[#0a0c10] transition hover:brightness-110 disabled:opacity-40"
          >
            {video.estado === 'completed' ? 'Reprocesar' : 'Procesar'}
          </button>
        )}
        <button
          type="button"
          onClick={onDelete}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition hover:border-rose-400/40 hover:text-rose-300"
        >
          Eliminar
        </button>
      </div>
    </article>
  )
}

function StatusBadge({ status }: { status: Video['estado'] }) {
  const colors: Record<Video['estado'], string> = {
    uploaded: 'bg-slate-500/20 text-slate-300',
    extracting_audio: 'bg-amber-500/20 text-amber-300',
    transcribing: 'bg-violet-500/20 text-violet-300',
    analyzing: 'bg-blue-500/20 text-blue-300',
    generating_clips: 'bg-cyan-500/20 text-cyan-300',
    adding_subtitles: 'bg-teal-500/20 text-teal-300',
    completed: 'bg-emerald-500/20 text-emerald-300',
    failed: 'bg-rose-500/20 text-rose-300',
  }
  return (
    <span
      className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${colors[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}
