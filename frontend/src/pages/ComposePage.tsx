import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  composeStreamUrl,
  getComposeJob,
  getComposeSource,
  startComposeSplit,
  type CropBoxNorm,
} from '../api/compose'
import { listVideos } from '../api/client'
import { CropEditor } from '../components/compose/CropEditor'
import { SplitPreview } from '../components/compose/SplitPreview'
import { ProgressBar } from '../components/ProgressBar'
import { FORMAT_LABELS, type ClipFormat } from '../types'
import { formatDuration } from '../utils/format'

const FORMATS: ClipFormat[] = ['vertical_9_16', 'portrait_4_5', 'square_1_1']

function defaultBoxes(): { top: CropBoxNorm; bottom: CropBoxNorm } {
  // Arriba: mitad superior · Abajo: mitad inferior (típico reacción)
  return {
    top: { x: 0.2, y: 0.02, w: 0.6, h: 0.45 },
    bottom: { x: 0.15, y: 0.5, w: 0.7, h: 0.48 },
  }
}

function panelAspectFor(format: ClipFormat): number {
  // Cada panel es mitad de la altura de salida
  if (format === 'vertical_9_16') return 1080 / 960 // 1.125
  if (format === 'portrait_4_5') return 1080 / 675 // 1.6
  if (format === 'square_1_1') return 1080 / 540 // 2
  return 1920 / 540
}

export function ComposePage() {
  const queryClient = useQueryClient()
  const [videoId, setVideoId] = useState<number | null>(null)
  const [format, setFormat] = useState<ClipFormat>('vertical_9_16')
  const [active, setActive] = useState<'top' | 'bottom'>('top')
  const boxes0 = useMemo(() => defaultBoxes(), [])
  const [top, setTop] = useState<CropBoxNorm>(boxes0.top)
  const [bottom, setBottom] = useState<CropBoxNorm>(boxes0.bottom)
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(30)
  const [duration, setDuration] = useState(0)
  const [time, setTime] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [doneClipId, setDoneClipId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const videosQuery = useQuery({
    queryKey: ['videos'],
    queryFn: listVideos,
  })

  const sourceQuery = useQuery({
    queryKey: ['compose-source', videoId],
    queryFn: () => getComposeSource(videoId!),
    enabled: videoId != null,
  })

  const jobQuery = useQuery({
    queryKey: ['compose-job', jobId],
    queryFn: () => getComposeJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed') return false
      return 900
    },
  })

  useEffect(() => {
    if (!videoId && videosQuery.data?.length) {
      setVideoId(videosQuery.data[0].id)
    }
  }, [videosQuery.data, videoId])

  useEffect(() => {
    const d = sourceQuery.data?.duracion
    if (d && d > 0) {
      setDuration(d)
      setStart(0)
      setEnd(Math.min(60, d))
      setTop(boxes0.top)
      setBottom(boxes0.bottom)
      setDoneClipId(null)
      setError(null)
    }
  }, [sourceQuery.data?.id, boxes0, sourceQuery.data?.duracion])

  useEffect(() => {
    const job = jobQuery.data
    if (!job || !jobId) return
    if (job.status === 'completed' && job.clip_id) {
      setDoneClipId(job.clip_id)
      setJobId(null)
      queryClient.invalidateQueries({ queryKey: ['clips'] })
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al componer')
      setJobId(null)
    }
  }, [jobQuery.data, jobId, queryClient])

  const exportMutation = useMutation({
    mutationFn: () =>
      startComposeSplit({
        video_id: videoId!,
        format,
        start,
        end: Math.max(start + 0.5, end),
        top,
        bottom,
        title: `Split ${FORMAT_LABELS[format].split('·')[0].trim()}`,
      }),
    onMutate: () => {
      setError(null)
      setDoneClipId(null)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const streamUrl = videoId != null ? composeStreamUrl(videoId) : ''
  const busy = jobId != null || exportMutation.isPending
  const panelAr = panelAspectFor(format)

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-violet-400/90">
          Función separada
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
          Composición manual
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Elige qué parte del video va arriba y cuál abajo (ideal para reacciones).
          Independiente del Studio de clips IA: aquí tú controlas los recortes.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
        <label className="block min-w-[220px] flex-1 space-y-1.5">
          <span className="text-xs text-slate-500">Video fuente</span>
          <select
            value={videoId ?? ''}
            disabled={busy}
            onChange={(e) => setVideoId(Number(e.target.value) || null)}
            className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
          >
            {!videosQuery.data?.length && <option value="">Sube un video en Studio primero</option>}
            {videosQuery.data?.map((v) => (
              <option key={v.id} value={v.id}>
                {v.nombre_original} ({formatDuration(v.duracion)})
              </option>
            ))}
          </select>
        </label>

        <div className="space-y-1.5">
          <span className="text-xs text-slate-500">Formato de salida</span>
          <div className="flex flex-wrap gap-2">
            {FORMATS.map((f) => (
              <button
                key={f}
                type="button"
                disabled={busy}
                onClick={() => setFormat(f)}
                className={[
                  'rounded-lg border px-3 py-2 text-xs transition',
                  format === f
                    ? 'border-violet-400/50 bg-violet-400/10 text-violet-100'
                    : 'border-white/8 text-slate-400 hover:border-white/20',
                ].join(' ')}
              >
                {FORMAT_LABELS[f].split('·')[0].trim()}
              </button>
            ))}
          </div>
        </div>

        <Link
          to="/studio"
          className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-400 hover:border-white/20 hover:text-white"
        >
          Ir a Studio (subir)
        </Link>
      </div>

      {!videoId && (
        <p className="rounded-xl border border-dashed border-white/10 px-4 py-12 text-center text-sm text-slate-500">
          No hay videos. Sube uno en{' '}
          <Link to="/studio" className="text-cyan-400 hover:underline">
            Studio
          </Link>{' '}
          y vuelve aquí.
        </p>
      )}

      {videoId && streamUrl && (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['top', 'Editar zona ARRIBA', 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200'],
                  ['bottom', 'Editar zona ABAJO', 'border-amber-400/40 bg-amber-400/10 text-amber-200'],
                ] as const
              ).map(([id, label, cls]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActive(id)}
                  className={[
                    'rounded-lg border px-3 py-1.5 text-xs transition',
                    active === id ? cls : 'border-white/8 text-slate-500',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>

            <CropEditor
              videoUrl={streamUrl}
              top={top}
              bottom={bottom}
              active={active}
              panelAspect={panelAr}
              onChangeTop={setTop}
              onChangeBottom={setBottom}
              onActiveChange={setActive}
              onTimeUpdate={setTime}
              onDuration={(d) => {
                setDuration(d)
                if (end > d) setEnd(d)
              }}
            />

            <div className="grid gap-4 rounded-xl border border-white/8 bg-white/[0.03] p-4 sm:grid-cols-2">
              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-slate-500">Inicio del clip (s)</span>
                <input
                  type="number"
                  min={0}
                  max={Math.max(0, duration - 0.5)}
                  step={0.1}
                  value={Number(start.toFixed(1))}
                  disabled={busy}
                  onChange={(e) => setStart(Math.max(0, Number(e.target.value)))}
                  className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-white"
                />
              </label>
              <label className="space-y-1.5 text-sm">
                <span className="text-xs text-slate-500">Fin del clip (s)</span>
                <input
                  type="number"
                  min={0.5}
                  max={duration || 99999}
                  step={0.1}
                  value={Number(end.toFixed(1))}
                  disabled={busy}
                  onChange={(e) => setEnd(Math.max(0.5, Number(e.target.value)))}
                  className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-white"
                />
              </label>
              <p className="sm:col-span-2 text-[11px] text-slate-500">
                Duración exportada: {formatDuration(Math.max(0, end - start))}
                {duration > 0 ? ` · Video total ${formatDuration(duration)}` : ''}
                {' · '}
                Reproduce el video arriba para ubicar la cara y el contenido de reacción.
              </p>
            </div>

            <button
              type="button"
              disabled={busy || !videoId || end <= start}
              onClick={() => exportMutation.mutate()}
              className="rounded-xl bg-gradient-to-r from-violet-500 to-fuchsia-500 px-5 py-3 text-sm font-medium text-white disabled:opacity-40"
            >
              {busy ? 'Exportando…' : 'Exportar composición split'}
            </button>

            {(busy || jobQuery.data) && jobId && (
              <div className="rounded-xl border border-violet-400/20 bg-violet-400/5 p-4">
                <ProgressBar
                  progress={jobQuery.data?.progress ?? 5}
                  label="Composición"
                  detail={jobQuery.data?.detail}
                />
              </div>
            )}

            {error && <p className="text-sm text-rose-400">{error}</p>}

            {doneClipId && (
              <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                Clip generado #{doneClipId}.{' '}
                <Link to="/library" className="underline hover:text-white">
                  Ver en Biblioteca
                </Link>
                {' · '}
                <Link
                  to={`/library/clips/${doneClipId}`}
                  className="underline hover:text-white"
                >
                  Abrir workspace
                </Link>
              </div>
            )}
          </div>

          <div className="lg:sticky lg:top-24 lg:self-start">
            <SplitPreview
              videoUrl={streamUrl}
              format={format}
              top={top}
              bottom={bottom}
              currentTime={time}
            />
            <ul className="mt-4 space-y-1.5 text-[11px] text-slate-500">
              <li>
                <span className="text-cyan-300">Arriba</span>: zona del streamer / cara
              </li>
              <li>
                <span className="text-amber-300">Abajo</span>: foto o video de reacción
              </li>
              <li>El recorte se adapta al formato elegido (TikTok, Feed, etc.)</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
