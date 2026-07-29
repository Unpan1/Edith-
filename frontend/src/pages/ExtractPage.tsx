import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getExtractJob, startYoutubeExtract, type YoutubeTranscriptResult } from '../api/extract'
import { ProgressBar } from '../components/ProgressBar'
import { formatDuration } from '../utils/format'

const SOURCE_LABELS: Record<string, string> = {
  captions: 'Subtítulos del video',
  auto_captions: 'Subtítulos automáticos de YouTube',
  whisper: 'Whisper (transcripción local mejorada)',
}

export function ExtractPage() {
  const [url, setUrl] = useState('')
  const [language, setLanguage] = useState('es')
  const [preferWhisper, setPreferWhisper] = useState(false)
  const [detectSpeakers, setDetectSpeakers] = useState(true)
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<YoutubeTranscriptResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const jobQuery = useQuery({
    queryKey: ['extract-job', jobId],
    queryFn: () => getExtractJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed') return false
      return 1000
    },
  })

  useEffect(() => {
    const job = jobQuery.data
    if (!job || !jobId) return
    if (job.status === 'completed' && job.result) {
      setResult(job.result)
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al extraer')
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const extractMutation = useMutation({
    mutationFn: () =>
      startYoutubeExtract({
        url: url.trim(),
        language: language || null,
        prefer_whisper: preferWhisper,
        detect_speakers: detectSpeakers,
      }),
    onMutate: () => {
      setError(null)
      setResult(null)
      setCopied(false)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const busy = jobId != null || extractMutation.isPending

  const downloadTxt = () => {
    if (!result?.text) return
    const blob = new Blob([result.text], { type: 'text/plain;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${(result.title || 'youtube').slice(0, 60)}.txt`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const copyText = async () => {
    if (!result?.text) return
    await navigator.clipboard.writeText(result.text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-sky-400/90">
          Función externa · Gratis
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
          Extraer texto de YouTube
        </h1>
        <p className="mt-2 max-w-xl text-sm text-slate-400">
          Pega un link y obtén el texto. Mejora de comprensión con Whisper y detección de
          hablantes distintos (local, sin APIs de pago).
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

        <div className="flex flex-wrap items-end gap-4">
          <label className="space-y-1.5">
            <span className="text-xs text-slate-500">Idioma</span>
            <select
              value={language}
              disabled={busy}
              onChange={(e) => setLanguage(e.target.value)}
              className="rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
            >
              <option value="es">Español (recomendado)</option>
              <option value="en">English</option>
              <option value="pt">Português</option>
              <option value="fr">Français</option>
              <option value="">Auto</option>
            </select>
          </label>

          <label className="flex cursor-pointer items-center gap-2 pb-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={detectSpeakers}
              disabled={busy}
              onChange={(e) => setDetectSpeakers(e.target.checked)}
              className="accent-sky-400"
            />
            Detectar hablantes distintos
          </label>

          <label className="flex cursor-pointer items-center gap-2 pb-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={preferWhisper}
              disabled={busy}
              onChange={(e) => setPreferWhisper(e.target.checked)}
              className="accent-sky-400"
            />
            Forzar Whisper (más preciso, más lento)
          </label>
        </div>

        <button
          type="button"
          disabled={busy || url.trim().length < 10}
          onClick={() => extractMutation.mutate()}
          className="rounded-xl bg-gradient-to-r from-sky-500 to-cyan-500 px-5 py-2.5 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
        >
          {busy ? 'Extrayendo…' : 'Extraer texto'}
        </button>

        {busy && (
          <ProgressBar
            progress={jobQuery.data?.progress ?? 8}
            label="Extracción"
            detail={jobQuery.data?.detail || 'Iniciando…'}
            etaSeconds={jobQuery.data?.eta_seconds}
          />
        )}

        {error && <p className="text-sm text-rose-400">{error}</p>}
      </section>

      {result && (
        <section className="space-y-3 rounded-2xl border border-sky-500/25 bg-sky-500/5 p-4 sm:p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-medium text-white">{result.title}</h2>
              <p className="mt-1 text-xs text-slate-500">
                {SOURCE_LABELS[result.source] || result.source}
                {result.language ? ` · idioma ${result.language}` : ''}
                {result.duration != null ? ` · ${formatDuration(result.duration)}` : ''}
                {result.cues?.length ? ` · ${result.cues.length} segmentos` : ''}
                {' · '}
                <span className={result.speakers_count > 1 ? 'text-cyan-300' : ''}>
                  {result.speakers_count > 1
                    ? `${result.speakers_count} hablantes detectados`
                    : '1 hablante'}
                </span>
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={copyText}
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:border-white/25"
              >
                {copied ? 'Copiado' : 'Copiar'}
              </button>
              <button
                type="button"
                onClick={downloadTxt}
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:border-white/25"
              >
                Descargar .txt
              </button>
              <Link
                to="/voices"
                className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs text-emerald-200 hover:bg-emerald-400/20"
              >
                Usar en Voces
              </Link>
            </div>
          </div>

          <textarea
            readOnly
            value={result.text}
            rows={16}
            className="w-full rounded-xl border border-white/10 bg-[#0d1018] px-4 py-3 text-sm leading-relaxed text-slate-200"
          />
        </section>
      )}
    </div>
  )
}
