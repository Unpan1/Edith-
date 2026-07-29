import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import {
  cancelStoryJob,
  getStoryJob,
  getStoryOptions,
  startStoryGenerate,
  storyVideoUrl,
  type StoryFormat,
  type StoryPreset,
} from '../api/stories'
import { listVoices } from '../api/voices'
import { ProgressBar } from '../components/ProgressBar'

const FALLBACK_PRESETS: { id: StoryPreset; label: string; description: string }[] = [
  { id: 'narracion', label: 'Narración', description: 'Relato claro, ritmo medio' },
  { id: 'misterio', label: 'Misterio', description: 'Atmósfera oscura' },
  { id: 'motivacional', label: 'Motivacional', description: 'Energía alta' },
  { id: 'terror', label: 'Terror', description: 'Oscuro y lento' },
  { id: 'documental', label: 'Documental', description: 'Sobrio y limpio' },
  { id: 'humor', label: 'Humor', description: 'Ritmo ágil' },
]

export function StoriesPage() {
  const [story, setStory] = useState(
    'Había una vez un pueblo al borde del bosque. Cada noche, una luz bailaba entre los árboles. Nadie se atrevía a seguirla… hasta que Ana decidió descubrir la verdad.',
  )
  const [preset, setPreset] = useState<StoryPreset>('misterio')
  const [instructions, setInstructions] = useState(
    'Vertical estilo TikTok, tono oscuro, ritmo pausado, voz envolvente',
  )
  const [format, setFormat] = useState<StoryFormat>('9:16')
  const [voiceId, setVoiceId] = useState('es-MX-DaliaNeural')
  const [mood, setMood] = useState('neutral')
  const [language, setLanguage] = useState('es')
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [resultMeta, setResultMeta] = useState<{
    scenes?: number
    duration?: number
  } | null>(null)

  const optionsQuery = useQuery({
    queryKey: ['story-options'],
    queryFn: getStoryOptions,
    staleTime: 60_000,
  })

  const voicesQuery = useQuery({
    queryKey: ['voices'],
    queryFn: listVoices,
    staleTime: 60_000,
  })

  const presets = optionsQuery.data?.presets?.length
    ? optionsQuery.data.presets
    : FALLBACK_PRESETS
  const voices = voicesQuery.data?.voices ?? []
  const moods = voicesQuery.data?.moods ?? []

  const jobQuery = useQuery({
    queryKey: ['story-job', jobId],
    queryFn: () => getStoryJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed' || st === 'cancelled') return false
      return 1200
    },
  })

  useEffect(() => {
    const job = jobQuery.data
    if (!job || !jobId) return
    if (job.status === 'completed' && job.stream_url) {
      const t = Date.now()
      setVideoUrl(storyVideoUrl(job.stream_url) + `?t=${t}`)
      setDownloadUrl(
        job.download_url ? storyVideoUrl(job.download_url) : storyVideoUrl(job.stream_url),
      )
      setResultMeta({
        scenes: job.scenes_count ?? undefined,
        duration: job.duration_seconds ?? undefined,
      })
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al generar el video')
      setJobId(null)
    } else if (job.status === 'cancelled') {
      setError(null)
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const generateMutation = useMutation({
    mutationFn: () =>
      startStoryGenerate({
        story: story.trim(),
        preset,
        instructions: instructions.trim(),
        format,
        voice_id: voiceId,
        mood,
        language,
      }),
    onMutate: () => {
      setError(null)
      setVideoUrl(null)
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
    mutationFn: () => cancelStoryJob(jobId!),
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

  const busy = jobId != null || generateMutation.isPending
  const canGenerate = story.trim().length >= 20 && !busy
  const canCancel = jobId != null && !cancelMutation.isPending

  const progress = jobQuery.data?.progress ?? (generateMutation.isPending ? 1 : 0)
  const detail = jobQuery.data?.detail ?? (generateMutation.isPending ? 'Enviando…' : '')

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-amber-400/90">
          Función separada · Gratis
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
          Historias → Video
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Escribe tu historia y explica el tipo de video. Se genera un MP4 narrado con
          escenas, voz y visuales (sin APIs de pago).
        </p>
      </div>

      <section className="space-y-4 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
        <label className="block space-y-1.5">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-medium text-white">Tu historia</span>
            <span className="font-mono text-[11px] text-slate-500">
              {story.length} / 20000
            </span>
          </div>
          <textarea
            value={story}
            maxLength={20000}
            rows={8}
            disabled={busy}
            onChange={(e) => setStory(e.target.value)}
            placeholder="Pega o escribe la historia completa…"
            className="w-full resize-y rounded-xl border border-white/10 bg-[#0d1018] px-4 py-3 text-sm leading-relaxed text-white placeholder:text-slate-600 focus:border-amber-400/40 focus:outline-none"
          />
        </label>

        <div>
          <p className="text-xs text-slate-500">Tipo de video (preset)</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {presets.map((p) => {
              const id = p.id as StoryPreset
              const on = preset === id
              return (
                <button
                  key={p.id}
                  type="button"
                  disabled={busy}
                  onClick={() => setPreset(id)}
                  className={[
                    'rounded-xl border px-3 py-2.5 text-left transition',
                    on
                      ? 'border-amber-400/45 bg-amber-400/10'
                      : 'border-white/8 bg-black/20 hover:border-white/20',
                  ].join(' ')}
                >
                  <span className="text-sm text-white">{p.label}</span>
                  <p className="mt-0.5 text-[11px] text-slate-500">{p.description}</p>
                </button>
              )
            })}
          </div>
        </div>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-white">
            Explica el tipo de video
          </span>
          <textarea
            value={instructions}
            maxLength={1000}
            rows={3}
            disabled={busy}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Ej: vertical TikTok, ritmo rápido, tono oscuro, estilo documental…"
            className="w-full resize-y rounded-xl border border-white/10 bg-[#0d1018] px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:border-amber-400/40 focus:outline-none"
          />
          <p className="text-[11px] text-slate-600">
            Palabras clave útiles: rápido, lento, oscuro, claro, frases cortas, TikTok…
          </p>
        </label>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Formato</span>
            <select
              value={format}
              disabled={busy}
              onChange={(e) => setFormat(e.target.value as StoryFormat)}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            >
              <option value="9:16">9:16 Vertical</option>
              <option value="16:9">16:9 Horizontal</option>
              <option value="1:1">1:1 Cuadrado</option>
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Idioma</span>
            <select
              value={language}
              disabled={busy}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            >
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Voz</span>
            <select
              value={voiceId}
              disabled={busy}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            >
              {voices.length === 0 && (
                <option value="es-MX-DaliaNeural">Dalia (MX)</option>
              )}
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.locale})
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Modo de habla</span>
            <select
              value={mood}
              disabled={busy}
              onChange={(e) => setMood(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            >
              {moods.length === 0 && <option value="neutral">Neutral</option>}
              {moods.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button
            type="button"
            disabled={!canGenerate}
            onClick={() => generateMutation.mutate()}
            className="rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 px-5 py-2.5 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
          >
            {busy ? 'Generando…' : 'Generar video'}
          </button>
          {canCancel && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-5 py-2.5 text-sm font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-40"
            >
              {cancelMutation.isPending ? 'Cancelando…' : 'Cancelar generación'}
            </button>
          )}
          {optionsQuery.data?.note && (
            <p className="text-[11px] text-slate-600">{optionsQuery.data.note}</p>
          )}
        </div>
      </section>

      {busy && (
        <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
          <ProgressBar
            progress={progress}
            label={detail || 'Generando video…'}
            etaSeconds={jobQuery.data?.eta_seconds}
          />
          {canCancel && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-rose-300 hover:border-rose-400/40 hover:text-rose-200 disabled:opacity-40"
            >
              {cancelMutation.isPending ? 'Cancelando…' : 'Cancelar'}
            </button>
          )}
        </div>
      )}

      {error && <p className="text-sm text-rose-400">{error}</p>}

      {videoUrl && (
        <section className="space-y-3 rounded-2xl border border-amber-500/25 bg-amber-500/5 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-amber-100">Video generado</h2>
            {resultMeta && (
              <span className="text-xs text-slate-500">
                {resultMeta.scenes != null && `${resultMeta.scenes} escenas`}
                {resultMeta.duration != null &&
                  ` · ${resultMeta.duration.toFixed(1)} s`}
              </span>
            )}
          </div>
          <video
            key={videoUrl}
            controls
            autoPlay
            className="mx-auto max-h-[70vh] w-full max-w-md rounded-xl bg-black"
            src={videoUrl}
          />
          {downloadUrl && (
            <a
              href={downloadUrl}
              download
              className="inline-flex text-xs text-amber-300 underline hover:text-white"
            >
              Descargar MP4
            </a>
          )}
        </section>
      )}
    </div>
  )
}
