import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  cancelConvertJob,
  convertFileUrl,
  formatBytes,
  getConvertJob,
  startYoutubeConvert,
  type ConvertFile,
  type ConvertFormat,
} from '../api/convert'
import { ProgressBar } from '../components/ProgressBar'

export function ConvertPage() {
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState<ConvertFormat>('both')
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [files, setFiles] = useState<ConvertFile[]>([])
  const [title, setTitle] = useState<string | null>(null)
  const [duration, setDuration] = useState<number | null>(null)

  const jobQuery = useQuery({
    queryKey: ['convert-job', jobId],
    queryFn: () => getConvertJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed' || st === 'cancelled') return false
      return 1000
    },
  })

  useEffect(() => {
    const job = jobQuery.data
    if (!job || !jobId) return
    if (job.status === 'completed') {
      setFiles(job.files || [])
      setTitle(job.title || null)
      setDuration(job.duration ?? null)
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al convertir')
      setJobId(null)
    } else if (job.status === 'cancelled') {
      setError(null)
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const startMutation = useMutation({
    mutationFn: () =>
      startYoutubeConvert({
        url: url.trim(),
        format,
      }),
    onMutate: () => {
      setError(null)
      setFiles([])
      setTitle(null)
      setDuration(null)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelConvertJob(jobId!),
    onSuccess: () => {
      setJobId(null)
      setError(null)
    },
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const busy = jobId != null || startMutation.isPending
  const canStart = url.trim().length >= 10 && !busy
  const canCancel = jobId != null && !cancelMutation.isPending
  const progress = jobQuery.data?.progress ?? (startMutation.isPending ? 1 : 0)
  const detail =
    jobQuery.data?.detail ?? (startMutation.isPending ? 'Enviando…' : '')

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-rose-400/90">
          Función separada · Gratis
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
          YouTube → MP4 / MP3
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-400">
          Pega un link de YouTube y descárgalo como video (MP4), audio (MP3) o ambos.
          Usa yt-dlp + FFmpeg, sin APIs de pago.
        </p>
      </div>

      <section className="space-y-4 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
        <label className="block space-y-1.5">
          <span className="text-xs text-slate-500">Link de YouTube</span>
          <input
            type="url"
            value={url}
            disabled={busy}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=… o youtu.be/…"
            className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2.5 text-sm text-white placeholder:text-slate-600"
          />
        </label>

        <div>
          <p className="text-xs text-slate-500">Formato de salida</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {(
              [
                ['both', 'MP4 + MP3'],
                ['mp4', 'Solo MP4'],
                ['mp3', 'Solo MP3'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                disabled={busy}
                onClick={() => setFormat(id)}
                className={[
                  'rounded-xl border px-4 py-2 text-sm transition',
                  format === id
                    ? 'border-rose-400/45 bg-rose-400/10 text-rose-100'
                    : 'border-white/8 text-slate-400 hover:border-white/20',
                ].join(' ')}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={!canStart}
            onClick={() => startMutation.mutate()}
            className="rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy ? 'Convirtiendo…' : 'Convertir'}
          </button>
          {canCancel && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-5 py-2.5 text-sm font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-40"
            >
              {cancelMutation.isPending ? 'Cancelando…' : 'Cancelar'}
            </button>
          )}
        </div>
      </section>

      {busy && (
        <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
          <ProgressBar
            progress={progress}
            label={detail || 'Convirtiendo…'}
            etaSeconds={jobQuery.data?.eta_seconds}
          />
          {canCancel && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-rose-300 hover:border-rose-400/40 disabled:opacity-40"
            >
              {cancelMutation.isPending ? 'Cancelando…' : 'Cancelar'}
            </button>
          )}
        </div>
      )}

      {error && <p className="text-sm text-rose-400">{error}</p>}

      {files.length > 0 && (
        <section className="space-y-4 rounded-2xl border border-rose-500/25 bg-rose-500/5 p-4 sm:p-5">
          <div>
            <h2 className="text-sm font-medium text-rose-100">Listo para descargar</h2>
            {(title || duration != null) && (
              <p className="mt-1 text-xs text-slate-500">
                {title}
                {duration != null && ` · ${Math.round(duration)} s`}
              </p>
            )}
          </div>

          <ul className="space-y-3">
            {files.map((f) => (
              <li
                key={f.filename}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/25 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-medium text-white uppercase">{f.kind}</p>
                  <p className="text-[11px] text-slate-500">
                    {f.display_name || f.filename} · {formatBytes(f.size_bytes)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {f.kind === 'mp4' && (
                    <a
                      href={convertFileUrl(f.stream_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:border-white/30"
                    >
                      Ver
                    </a>
                  )}
                  {f.kind === 'mp3' && (
                    <audio
                      controls
                      className="h-8 max-w-[220px]"
                      src={convertFileUrl(f.stream_url)}
                    />
                  )}
                  <a
                    href={convertFileUrl(f.download_url)}
                    download
                    className="rounded-lg bg-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-100 hover:bg-rose-500/30"
                  >
                    Descargar {f.kind.toUpperCase()}
                  </a>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
