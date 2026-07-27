import { STATUS_LABELS, type VideoStatus } from '../types'

interface ProgressBarProps {
  progress: number
  status?: VideoStatus
  label?: string
  detail?: string | null
  etaSeconds?: number | null
  steps?: { id: string; label: string; state: 'done' | 'active' | 'pending' }[]
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `~${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m < 60) return s > 0 ? `~${m}m ${s}s` : `~${m} min`
  const h = Math.floor(m / 60)
  const rm = m % 60
  return rm > 0 ? `~${h}h ${rm}m` : `~${h}h`
}

export function ProgressBar({
  progress,
  status,
  label,
  detail,
  etaSeconds,
  steps,
}: ProgressBarProps) {
  const pct = Math.max(0, Math.min(100, Math.round(progress)))
  const statusLabel = label ?? (status ? STATUS_LABELS[status] : undefined)

  return (
    <div className="w-full space-y-2.5">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="truncate text-slate-300">{statusLabel ?? 'Progreso'}</span>
        <div className="flex shrink-0 items-center gap-2 font-mono">
          {etaSeconds != null && etaSeconds > 0 && (
            <span className="text-slate-500">{formatEta(etaSeconds)}</span>
          )}
          <span className="text-cyan-300">{pct}%</span>
        </div>
      </div>

      <div className="h-2.5 overflow-hidden rounded-full bg-white/8">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-400 transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {detail && (
        <p className="text-[11px] leading-snug text-slate-400">{detail}</p>
      )}

      {steps && steps.length > 0 && (
        <ol className="space-y-1 border-t border-white/6 pt-2">
          {steps.map((step) => (
            <li
              key={step.id}
              className={[
                'flex items-center gap-2 text-[11px]',
                step.state === 'done'
                  ? 'text-emerald-400/90'
                  : step.state === 'active'
                    ? 'text-cyan-300'
                    : 'text-slate-600',
              ].join(' ')}
            >
              <span className="w-3 text-center">
                {step.state === 'done' ? '✓' : step.state === 'active' ? '›' : '·'}
              </span>
              <span className={step.state === 'active' ? 'font-medium' : undefined}>
                {step.label}
              </span>
              {step.state === 'active' && (
                <span className="ml-auto animate-pulse text-[10px] text-slate-500">
                  en curso
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

/** Pasos del pipeline de procesamiento para la UI. */
export function buildProcessSteps(status?: VideoStatus) {
  const order: VideoStatus[] = [
    'extracting_audio',
    'transcribing',
    'analyzing',
    'generating_clips',
    'adding_subtitles',
  ]
  const labels: Record<string, string> = {
    extracting_audio: 'Extraer audio',
    transcribing: 'Transcribir (Whisper)',
    analyzing: 'Analizar / dividir',
    generating_clips: 'Generar clips',
    adding_subtitles: 'Subtítulos y acabado',
  }

  if (!status || status === 'uploaded' || status === 'completed' || status === 'failed') {
    return order.map((id) => ({
      id,
      label: labels[id],
      state: (status === 'completed' ? 'done' : 'pending') as 'done' | 'pending',
    }))
  }

  const idx = order.indexOf(status)
  return order.map((id, i) => ({
    id,
    label: labels[id],
    state: (i < idx ? 'done' : i === idx ? 'active' : 'pending') as
      | 'done'
      | 'active'
      | 'pending',
  }))
}

export function buildYoutubeSteps(progress: number, status: string) {
  const steps = [
    { id: 'info', label: 'Obtener info del video', threshold: 5 },
    { id: 'download', label: 'Descargar video', threshold: 90 },
    { id: 'merge', label: 'Unir pistas / validar', threshold: 97 },
    { id: 'save', label: 'Guardar en biblioteca', threshold: 100 },
  ]
  if (status === 'completed') {
    return steps.map((s) => ({ id: s.id, label: s.label, state: 'done' as const }))
  }
  if (status === 'failed') {
    return steps.map((s) => ({
      id: s.id,
      label: s.label,
      state: (progress >= s.threshold ? 'done' : 'pending') as 'done' | 'pending',
    }))
  }
  let activeSet = false
  return steps.map((s) => {
    if (progress >= s.threshold) {
      return { id: s.id, label: s.label, state: 'done' as const }
    }
    if (!activeSet) {
      activeSet = true
      return { id: s.id, label: s.label, state: 'active' as const }
    }
    return { id: s.id, label: s.label, state: 'pending' as const }
  })
}
