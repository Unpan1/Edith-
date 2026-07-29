import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import {
  cancelVoiceJob,
  getVoiceJob,
  listVoices,
  previewVoice,
  startSynthesizeDialogue,
  startSynthesizeVoice,
  voiceAudioUrl,
  type SpeechMood,
  type VoiceInfo,
} from '../api/voices'
import { ProgressBar } from '../components/ProgressBar'

type Mode = 'single' | 'dialogue'

interface DialogueTurn {
  id: string
  character: string
  voice_id: string
  mood: string
  text: string
}

const FALLBACK_MOODS: SpeechMood[] = [
  { id: 'neutral', label: 'Neutral', rate: '+0%', pitch: '+0Hz' },
  { id: 'nervous', label: 'Nervioso', rate: '+18%', pitch: '+4Hz' },
  { id: 'anxious', label: 'Ansioso', rate: '+12%', pitch: '+3Hz' },
  { id: 'furious', label: 'Furioso', rate: '+8%', pitch: '-2Hz' },
  { id: 'shouting', label: 'Gritando', rate: '+15%', pitch: '+6Hz' },
  { id: 'sad', label: 'Triste', rate: '-15%', pitch: '-4Hz' },
  { id: 'cheerful', label: 'Alegre', rate: '+8%', pitch: '+3Hz' },
  { id: 'whisper', label: 'Susurrando', rate: '-8%', pitch: '-2Hz' },
]

const SPEED_PRESETS = [
  { label: 'Muy lenta', value: -40 },
  { label: 'Lenta', value: -20 },
  { label: 'Normal', value: 0 },
  { label: 'Rápida', value: 25 },
  { label: 'Muy rápida', value: 50 },
] as const

function speedLabel(speed: number): string {
  if (speed <= -35) return 'Muy lenta'
  if (speed <= -15) return 'Lenta'
  if (speed < 15) return 'Normal'
  if (speed < 40) return 'Rápida'
  return 'Muy rápida'
}

function speedMultiplier(speed: number): string {
  const x = 1 + speed / 100
  return `${x.toFixed(2)}×`
}

function newTurn(voiceId: string, index: number): DialogueTurn {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    character: `Personaje ${index}`,
    voice_id: voiceId,
    mood: 'neutral',
    text: '',
  }
}

export function VoicesPage() {
  const [mode, setMode] = useState<Mode>('single')
  const [text, setText] = useState(
    'Hola, esta es una prueba de narración con inteligencia artificial.',
  )
  const [voiceId, setVoiceId] = useState('es-MX-DaliaNeural')
  const [mood, setMood] = useState('neutral')
  const [speed, setSpeed] = useState(0)
  const [genderFilter, setGenderFilter] = useState<'all' | 'Female' | 'Male'>('all')
  const [localeFilter, setLocaleFilter] = useState<string>('es')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewMeta, setPreviewMeta] = useState<{ rate?: string; speed: number } | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [turns, setTurns] = useState<DialogueTurn[]>([
    {
      id: '1',
      character: 'Personaje 1',
      voice_id: 'es-MX-DaliaNeural',
      mood: 'cheerful',
      text: '¡Hola! ¿Viste lo que pasó ayer?',
    },
    {
      id: '2',
      character: 'Personaje 2',
      voice_id: 'es-MX-JorgeNeural',
      mood: 'nervous',
      text: 'Sí… la verdad es que estoy un poco nervioso de contarlo.',
    },
  ])
  const [pauseMs, setPauseMs] = useState(350)

  const voicesQuery = useQuery({
    queryKey: ['voices'],
    queryFn: listVoices,
    staleTime: 60_000,
  })

  const voices = voicesQuery.data?.voices ?? []
  const moods = voicesQuery.data?.moods?.length
    ? voicesQuery.data.moods
    : FALLBACK_MOODS

  const filtered = useMemo(() => {
    return voices.filter((v) => {
      if (genderFilter !== 'all' && v.gender !== genderFilter) return false
      if (localeFilter === 'es' && !v.locale.startsWith('es-')) return false
      if (localeFilter === 'en' && !v.locale.startsWith('en-')) return false
      return true
    })
  }, [voices, genderFilter, localeFilter])

  const selected: VoiceInfo | undefined =
    voices.find((v) => v.id === voiceId) || filtered[0]

  const jobQuery = useQuery({
    queryKey: ['voice-job', jobId],
    queryFn: () => getVoiceJob(jobId!),
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
      setAudioUrl(voiceAudioUrl(job.stream_url) + `?t=${t}`)
      setDownloadUrl(
        job.download_url
          ? voiceAudioUrl(job.download_url)
          : voiceAudioUrl(job.stream_url),
      )
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al generar la voz')
      setAudioUrl(null)
      setDownloadUrl(null)
      setJobId(null)
    } else if (job.status === 'cancelled') {
      setError(null)
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const startMutation = useMutation({
    mutationFn: async () => {
      if (mode === 'single') {
        return startSynthesizeVoice({
          text,
          voice_id: selected?.id || voiceId,
          mood,
          speed,
        })
      }
      return startSynthesizeDialogue({
        turns: turns
          .filter((t) => t.text.trim())
          .map((t) => ({
            voice_id: t.voice_id,
            text: t.text.trim(),
            mood: t.mood,
            character: t.character,
          })),
        pause_ms: pauseMs,
        speed,
      })
    },
    onMutate: () => {
      setError(null)
      setAudioUrl(null)
      setDownloadUrl(null)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
    },
  })

  const previewMutation = useMutation({
    mutationFn: () =>
      previewVoice({
        voice_id: selected?.id || voiceId,
        mood,
        speed,
      }),
    onMutate: () => setError(null),
    onSuccess: (res) => {
      const t = Date.now()
      setPreviewUrl(voiceAudioUrl(res.stream_url) + `?t=${t}`)
      setPreviewMeta({ rate: res.rate || undefined, speed: res.speed ?? speed })
    },
    onError: (err) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || (err as Error).message)
      setPreviewUrl(null)
      setPreviewMeta(null)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelVoiceJob(jobId!),
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
  const previewBusy = previewMutation.isPending
  const canCancel = jobId != null && !cancelMutation.isPending
  const canSingle = text.trim().length > 0 && !busy && !!selected
  const canDialogue =
    turns.some((t) => t.text.trim()) &&
    turns.filter((t) => t.text.trim()).length >= 1 &&
    !busy
  const canPreview = !busy && !previewBusy && !!selected

  const progress = jobQuery.data?.progress ?? (startMutation.isPending ? 1 : 0)
  const detail =
    jobQuery.data?.detail ?? (startMutation.isPending ? 'Enviando…' : '')

  const pickVoice = (id: string) => setVoiceId(id)

  const updateTurn = (id: string, patch: Partial<DialogueTurn>) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)))
  }

  const CancelButton = ({ className }: { className?: string }) =>
    canCancel ? (
      <button
        type="button"
        disabled={cancelMutation.isPending}
        onClick={() => cancelMutation.mutate()}
        className={
          className ||
          'rounded-xl border border-rose-400/40 bg-rose-500/10 px-5 py-2.5 text-sm font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-40'
        }
      >
        {cancelMutation.isPending ? 'Cancelando…' : 'Cancelar generación'}
      </button>
    ) : null

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-emerald-400/90">
          Función separada · Gratis
        </p>
        <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">Voces</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Narración simple o diálogo con varios personajes y modos de habla. Ajusta la
          velocidad y escucha una vista previa antes de generar todo el texto.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ['single', 'Una voz'],
            ['dialogue', 'Diálogo / historia'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            disabled={busy}
            onClick={() => setMode(id)}
            className={[
              'rounded-xl border px-4 py-2 text-sm transition',
              mode === id
                ? 'border-emerald-400/45 bg-emerald-400/10 text-emerald-100'
                : 'border-white/8 text-slate-400 hover:border-white/20',
            ].join(' ')}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['es', 'Español'],
                ['en', 'English'],
                ['all', 'Todas'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setLocaleFilter(id)}
                className={[
                  'rounded-lg border px-2.5 py-1 text-[11px] transition',
                  localeFilter === id
                    ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200'
                    : 'border-white/8 text-slate-500 hover:border-white/20',
                ].join(' ')}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['all', 'Todas'],
                ['Female', 'Mujer'],
                ['Male', 'Hombre'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setGenderFilter(id)}
                className={[
                  'rounded-lg border px-2.5 py-1 text-[11px] transition',
                  genderFilter === id
                    ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200'
                    : 'border-white/8 text-slate-500 hover:border-white/20',
                ].join(' ')}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="max-h-[480px] space-y-1.5 overflow-y-auto pr-1">
            {voicesQuery.isLoading && (
              <p className="text-xs text-slate-500">Cargando voces…</p>
            )}
            {filtered.map((v) => {
              const on = (selected?.id || voiceId) === v.id
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => pickVoice(v.id)}
                  className={[
                    'w-full rounded-xl border px-3 py-2.5 text-left transition',
                    on
                      ? 'border-emerald-400/45 bg-emerald-400/10'
                      : 'border-white/8 bg-black/20 hover:border-white/20',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-white">{v.name}</span>
                    <span className="text-[10px] uppercase text-slate-500">
                      {v.gender === 'Female' ? '♀' : '♂'} {v.locale}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{v.style}</p>
                </button>
              )
            })}
          </div>
        </aside>

        <section className="space-y-4">
          <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
            <h2 className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Modo de habla
            </h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {moods.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  disabled={busy || previewBusy}
                  onClick={() => setMood(m.id)}
                  className={[
                    'rounded-lg border px-3 py-1.5 text-xs transition',
                    mood === m.id
                      ? 'border-violet-400/50 bg-violet-400/15 text-violet-100'
                      : 'border-white/8 text-slate-400 hover:border-white/20',
                  ].join(' ')}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-sm font-medium text-white">Velocidad del narrador</h2>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {speedLabel(speed)} · {speedMultiplier(speed)}
                  {speed !== 0 ? ` (${speed > 0 ? '+' : ''}${speed}%)` : ''}
                </p>
              </div>
              <button
                type="button"
                disabled={!canPreview}
                onClick={() => previewMutation.mutate()}
                className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-medium text-cyan-100 hover:bg-cyan-400/20 disabled:opacity-40"
              >
                {previewBusy ? 'Generando previa…' : 'Vista previa'}
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {SPEED_PRESETS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  disabled={busy || previewBusy}
                  onClick={() => setSpeed(p.value)}
                  className={[
                    'rounded-lg border px-3 py-1.5 text-xs transition',
                    speed === p.value
                      ? 'border-emerald-400/50 bg-emerald-400/15 text-emerald-100'
                      : 'border-white/8 text-slate-400 hover:border-white/20',
                  ].join(' ')}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <label className="block space-y-2">
              <input
                type="range"
                min={-50}
                max={100}
                step={5}
                value={speed}
                disabled={busy || previewBusy}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="w-full accent-emerald-400"
              />
              <div className="flex justify-between text-[10px] uppercase tracking-wide text-slate-600">
                <span>Lenta</span>
                <span>Normal</span>
                <span>Rápida</span>
              </div>
            </label>

            <p className="text-[11px] text-slate-600">
              Prueba la voz y la velocidad con una frase corta antes de pegar todo tu texto.
              La velocidad se aplica también al diálogo completo.
            </p>

            {previewUrl && (
              <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/5 p-3">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-medium text-cyan-100">
                    Vista previa
                    {selected && ` · ${selected.name}`}
                    {` · ${moods.find((m) => m.id === mood)?.label || mood}`}
                    {` · ${speedLabel(previewMeta?.speed ?? speed)} (${speedMultiplier(previewMeta?.speed ?? speed)})`}
                  </p>
                  {previewMeta?.rate && (
                    <span className="font-mono text-[10px] text-slate-500">
                      rate {previewMeta.rate}
                    </span>
                  )}
                </div>
                <audio key={previewUrl} controls autoPlay className="w-full" src={previewUrl} />
              </div>
            )}
          </div>

          {mode === 'single' ? (
            <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="voice-text" className="text-sm font-medium text-white">
                  Texto a narrar
                </label>
                <span className="font-mono text-[11px] text-slate-500">
                  {text.length} / 20000
                </span>
              </div>
              <textarea
                id="voice-text"
                value={text}
                maxLength={20000}
                rows={10}
                disabled={busy}
                onChange={(e) => setText(e.target.value)}
                className="w-full resize-y rounded-xl border border-white/10 bg-[#0d1018] px-4 py-3 text-sm leading-relaxed text-white placeholder:text-slate-600 focus:border-emerald-400/40 focus:outline-none"
              />
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={!canSingle}
                  onClick={() => startMutation.mutate()}
                  className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-5 py-2.5 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
                >
                  {busy ? 'Generando…' : 'Generar narración'}
                </button>
                <CancelButton />
                {selected && (
                  <span className="text-xs text-slate-500">
                    {selected.name} · {moods.find((m) => m.id === mood)?.label || mood} ·{' '}
                    {speedLabel(speed)}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-sm font-medium text-white">Turnos del diálogo</h2>
                <label className="flex items-center gap-2 text-xs text-slate-500">
                  Pausa entre turnos
                  <select
                    value={pauseMs}
                    disabled={busy}
                    onChange={(e) => setPauseMs(Number(e.target.value))}
                    className="rounded-lg border border-white/10 bg-[#12151e] px-2 py-1 text-white"
                  >
                    <option value={200}>Corta</option>
                    <option value={350}>Normal</option>
                    <option value={600}>Larga</option>
                    <option value={1000}>Muy larga</option>
                  </select>
                </label>
              </div>

              {turns.map((turn, idx) => (
                <div
                  key={turn.id}
                  className="space-y-2 rounded-xl border border-white/10 bg-black/25 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-medium uppercase text-slate-500">
                      Turno {idx + 1}
                    </span>
                    <input
                      value={turn.character}
                      disabled={busy}
                      onChange={(e) => updateTurn(turn.id, { character: e.target.value })}
                      className="min-w-[120px] flex-1 rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-xs text-white"
                      placeholder="Nombre personaje"
                    />
                    <select
                      value={turn.voice_id}
                      disabled={busy}
                      onChange={(e) => updateTurn(turn.id, { voice_id: e.target.value })}
                      className="rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-xs text-white"
                    >
                      {voices.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} ({v.locale})
                        </option>
                      ))}
                    </select>
                    <select
                      value={turn.mood}
                      disabled={busy}
                      onChange={(e) => updateTurn(turn.id, { mood: e.target.value })}
                      className="rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-xs text-white"
                    >
                      {moods.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={busy || turns.length <= 1}
                      onClick={() => setTurns((p) => p.filter((t) => t.id !== turn.id))}
                      className="rounded-lg border border-white/10 px-2 py-1 text-[11px] text-rose-300 disabled:opacity-30"
                    >
                      Quitar
                    </button>
                  </div>
                  <textarea
                    value={turn.text}
                    disabled={busy}
                    rows={2}
                    maxLength={3000}
                    onChange={(e) => updateTurn(turn.id, { text: e.target.value })}
                    placeholder={`Qué dice ${turn.character}…`}
                    className="w-full rounded-lg border border-white/10 bg-[#0d1018] px-3 py-2 text-sm text-white"
                  />
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => updateTurn(turn.id, { voice_id: voiceId, mood })}
                    className="text-[10px] text-slate-500 underline hover:text-slate-300"
                  >
                    Usar voz/modo seleccionados arriba
                  </button>
                </div>
              ))}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || turns.length >= 40}
                  onClick={() =>
                    setTurns((p) => [...p, newTurn(voiceId || 'es-MX-DaliaNeural', p.length + 1)])
                  }
                  className="rounded-lg border border-white/15 px-3 py-2 text-xs text-slate-300 hover:border-white/30"
                >
                  + Añadir personaje / turno
                </button>
                <button
                  type="button"
                  disabled={!canDialogue}
                  onClick={() => startMutation.mutate()}
                  className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-5 py-2.5 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
                >
                  {busy ? 'Generando diálogo…' : 'Generar diálogo completo'}
                </button>
                <CancelButton />
              </div>
            </div>
          )}

          {busy && (
            <div className="space-y-3 rounded-2xl border border-white/8 bg-white/[0.03] p-4">
              <ProgressBar
                progress={progress}
                label={detail || 'Generando voz…'}
                etaSeconds={jobQuery.data?.eta_seconds}
              />
              <CancelButton className="rounded-lg border border-white/15 px-3 py-1.5 text-xs text-rose-300 hover:border-rose-400/40 hover:text-rose-200 disabled:opacity-40" />
            </div>
          )}

          {error && <p className="text-sm text-rose-400">{error}</p>}

          {audioUrl && (
            <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-4 sm:p-5">
              <h2 className="text-sm font-medium text-emerald-100">Escucha final</h2>
              <audio key={audioUrl} controls autoPlay className="mt-4 w-full" src={audioUrl} />
              <a
                href={downloadUrl || audioUrl}
                download
                className="mt-3 inline-flex text-xs text-emerald-300 underline hover:text-white"
              >
                Descargar MP3
              </a>
            </div>
          )}

          <p className="text-[11px] text-slate-600">
            {voicesQuery.data?.note ||
              'Los modos y la velocidad cambian ritmo, tono y volumen de la voz.'}
          </p>
        </section>
      </div>
    </div>
  )
}
