import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  cancelEditJob,
  editFileUrl,
  formatBytes,
  getEditJob,
  startEditRender,
  uploadEditAsset,
  type AudioMode,
  type EditAsset,
} from '../api/edit'
import { ProgressBar } from '../components/ProgressBar'

export function BasicEditPage() {
  const [videos, setVideos] = useState<EditAsset[]>([])
  const [audio, setAudio] = useState<EditAsset | null>(null)
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState<string>('')
  const [mirror, setMirror] = useState(false)
  const [videoVolume, setVideoVolume] = useState(100)
  const [audioVolume, setAudioVolume] = useState(100)
  const [audioMode, setAudioMode] = useState<AudioMode>('mix')
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [resultMeta, setResultMeta] = useState<{
    duration?: number
    size?: number
  } | null>(null)

  const totalDur = useMemo(() => {
    return videos.reduce((acc, v) => acc + (v.duration || 0), 0)
  }, [videos])

  const jobQuery = useQuery({
    queryKey: ['edit-job', jobId],
    queryFn: () => getEditJob(jobId!),
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
    if (job.status === 'completed' && job.stream_url) {
      const t = Date.now()
      setResultUrl(editFileUrl(job.stream_url) + `?t=${t}`)
      setDownloadUrl(
        job.download_url
          ? editFileUrl(job.download_url)
          : editFileUrl(job.stream_url),
      )
      setResultMeta({
        duration: job.duration ?? undefined,
        size: job.size_bytes ?? undefined,
      })
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al editar')
      setJobId(null)
    } else if (job.status === 'cancelled') {
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const uploadVideoMutation = useMutation({
    mutationFn: async (files: FileList | File[]) => {
      const list = Array.from(files)
      const uploaded: EditAsset[] = []
      for (const f of list) {
        setUploadPct(0)
        const asset = await uploadEditAsset(f, 'video', setUploadPct)
        uploaded.push(asset)
      }
      return uploaded
    },
    onSuccess: (assets) => {
      setVideos((prev) => [...prev, ...assets].slice(0, 12))
      setUploadPct(null)
      setError(null)
    },
    onError: (err) => {
      setUploadPct(null)
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const uploadAudioMutation = useMutation({
    mutationFn: (file: File) => uploadEditAsset(file, 'audio', setUploadPct),
    onSuccess: (asset) => {
      setAudio(asset)
      setUploadPct(null)
      setError(null)
    },
    onError: (err) => {
      setUploadPct(null)
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const renderMutation = useMutation({
    mutationFn: () =>
      startEditRender({
        video_ids: videos.map((v) => v.id),
        audio_id: audioMode === 'keep' ? null : audio?.id ?? null,
        start,
        end: end.trim() ? Number(end) : null,
        mirror,
        video_volume: videoVolume / 100,
        audio_volume: audioVolume / 100,
        audio_mode: audio ? audioMode : 'keep',
      }),
    onMutate: () => {
      setError(null)
      setResultUrl(null)
      setDownloadUrl(null)
      setResultMeta(null)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelEditJob(jobId!),
    onSuccess: () => setJobId(null),
  })

  const busy =
    jobId != null ||
    renderMutation.isPending ||
    uploadVideoMutation.isPending ||
    uploadAudioMutation.isPending
  const canRender = videos.length >= 1 && !busy
  const canCancel = jobId != null && !cancelMutation.isPending
  const progress = jobQuery.data?.progress ?? (renderMutation.isPending ? 1 : 0)
  const detail =
    jobQuery.data?.detail ?? (renderMutation.isPending ? 'Enviando…' : '')

  const moveVideo = (index: number, dir: -1 | 1) => {
    setVideos((prev) => {
      const next = [...prev]
      const j = index + dir
      if (j < 0 || j >= next.length) return prev
      ;[next[index], next[j]] = [next[j], next[index]]
      return next
    })
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-indigo-400/90">
          Función separada · Gratis
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
          Editor básico
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Pega videos, recorta, modo espejo y controla el volumen del video y de un audio
          externo. Todo local con FFmpeg.
        </p>
      </div>

      {/* Videos */}
      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-white">Videos (en orden)</h2>
          <label className="cursor-pointer rounded-lg border border-indigo-400/40 bg-indigo-400/10 px-3 py-1.5 text-xs text-indigo-100 hover:bg-indigo-400/20">
            + Añadir video
            <input
              type="file"
              accept="video/*,.mp4,.mov,.mkv,.webm,.avi"
              multiple
              disabled={busy}
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) uploadVideoMutation.mutate(e.target.files)
                e.target.value = ''
              }}
            />
          </label>
        </div>

        {videos.length === 0 && (
          <p className="text-xs text-slate-500">Sube uno o más videos para empezar.</p>
        )}

        <ul className="space-y-2">
          {videos.map((v, i) => (
            <li
              key={v.id}
              className="flex flex-wrap items-center gap-3 rounded-xl border border-white/10 bg-black/25 px-3 py-2"
            >
              <span className="text-[10px] font-medium uppercase text-slate-500">
                #{i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-white">{v.original_name}</p>
                <p className="text-[11px] text-slate-500">
                  {v.duration != null ? `${v.duration.toFixed(1)} s` : '—'}
                  {v.width && v.height ? ` · ${v.width}×${v.height}` : ''}
                  {` · ${formatBytes(v.size_bytes)}`}
                </p>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  disabled={busy || i === 0}
                  onClick={() => moveVideo(i, -1)}
                  className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-400 disabled:opacity-30"
                >
                  ↑
                </button>
                <button
                  type="button"
                  disabled={busy || i === videos.length - 1}
                  onClick={() => moveVideo(i, 1)}
                  className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-400 disabled:opacity-30"
                >
                  ↓
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => setVideos((p) => p.filter((x) => x.id !== v.id))}
                  className="rounded border border-white/10 px-2 py-1 text-[11px] text-rose-300"
                >
                  Quitar
                </button>
              </div>
            </li>
          ))}
        </ul>

        {videos[0] && (
          <video
            key={videos[0].id}
            controls
            className={[
              'mt-2 max-h-56 w-full rounded-xl bg-black',
              mirror ? 'scale-x-[-1]' : '',
            ].join(' ')}
            src={editFileUrl(videos[0].stream_url)}
          />
        )}
      </section>

      {/* Audio */}
      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-white">Audio externo (opcional)</h2>
          <label className="cursor-pointer rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:border-white/30">
            {audio ? 'Cambiar audio' : '+ Añadir audio'}
            <input
              type="file"
              accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg"
              disabled={busy}
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) uploadAudioMutation.mutate(f)
                e.target.value = ''
              }}
            />
          </label>
        </div>
        {audio ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm text-white">{audio.original_name}</p>
              <button
                type="button"
                disabled={busy}
                onClick={() => setAudio(null)}
                className="text-xs text-rose-300 underline"
              >
                Quitar
              </button>
            </div>
            <audio controls className="w-full" src={editFileUrl(audio.stream_url)} />
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['mix', 'Mezclar con video'],
                  ['replace', 'Reemplazar audio'],
                  ['keep', 'Ignorar (solo video)'],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  disabled={busy}
                  onClick={() => setAudioMode(id)}
                  className={[
                    'rounded-lg border px-3 py-1.5 text-xs',
                    audioMode === id
                      ? 'border-indigo-400/45 bg-indigo-400/10 text-indigo-100'
                      : 'border-white/8 text-slate-400',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500">
            Puedes pegar música o narración encima del video.
          </p>
        )}
      </section>

      {/* Controles */}
      <section className="space-y-4 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
        <h2 className="text-sm font-medium text-white">Recorte y efectos</h2>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Inicio (segundos)</span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={start}
              disabled={busy}
              onChange={(e) => setStart(Math.max(0, Number(e.target.value) || 0))}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            />
          </label>
          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">
              Fin (segundos){totalDur > 0 ? ` · total ~${totalDur.toFixed(1)}s` : ''}
            </span>
            <input
              type="number"
              min={0}
              step={0.1}
              value={end}
              disabled={busy}
              placeholder="Hasta el final"
              onChange={(e) => setEnd(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white placeholder:text-slate-600"
            />
          </label>
        </div>

        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={mirror}
            disabled={busy}
            onChange={(e) => setMirror(e.target.checked)}
            className="size-4 accent-indigo-400"
          />
          <span className="text-sm text-white">Modo espejo (horizontal)</span>
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-2">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Volumen del video</span>
              <span className="font-mono text-slate-300">{videoVolume}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={200}
              step={5}
              value={videoVolume}
              disabled={busy}
              onChange={(e) => setVideoVolume(Number(e.target.value))}
              className="w-full accent-indigo-400"
            />
          </label>
          <label className="space-y-2">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Volumen del audio externo</span>
              <span className="font-mono text-slate-300">{audioVolume}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={200}
              step={5}
              value={audioVolume}
              disabled={busy || !audio || audioMode === 'keep'}
              onChange={(e) => setAudioVolume(Number(e.target.value))}
              className="w-full accent-indigo-400"
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-3 pt-1">
          <button
            type="button"
            disabled={!canRender}
            onClick={() => renderMutation.mutate()}
            className="rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy && jobId ? 'Procesando…' : 'Exportar video'}
          </button>
          {canCancel && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-5 py-2.5 text-sm text-rose-200 disabled:opacity-40"
            >
              Cancelar
            </button>
          )}
        </div>
      </section>

      {(uploadPct != null || busy) && (
        <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
          <ProgressBar
            progress={uploadPct != null ? uploadPct : progress}
            label={
              uploadPct != null
                ? `Subiendo… ${uploadPct}%`
                : detail || 'Editando…'
            }
            etaSeconds={jobQuery.data?.eta_seconds}
          />
        </div>
      )}

      {error && <p className="text-sm text-rose-400">{error}</p>}

      {resultUrl && (
        <section className="space-y-3 rounded-2xl border border-indigo-500/25 bg-indigo-500/5 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-indigo-100">Resultado</h2>
            {resultMeta && (
              <span className="text-xs text-slate-500">
                {resultMeta.duration != null && `${resultMeta.duration.toFixed(1)} s`}
                {resultMeta.size != null && ` · ${formatBytes(resultMeta.size)}`}
              </span>
            )}
          </div>
          <video
            key={resultUrl}
            controls
            autoPlay
            className="max-h-[70vh] w-full rounded-xl bg-black"
            src={resultUrl}
          />
          {downloadUrl && (
            <a
              href={downloadUrl}
              download
              className="inline-flex text-xs text-indigo-300 underline hover:text-white"
            >
              Descargar MP4
            </a>
          )}
        </section>
      )}
    </div>
  )
}
