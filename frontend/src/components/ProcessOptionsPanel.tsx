import { ClipPreview } from './ClipPreview'
import type {
  ClipFormat,
  ContentMode,
  FillMode,
  InterviewLayout,
  ProcessOptions,
  ProcessingMode,
  SplitStrategy,
  SubtitlePosition,
  SubtitleStyle,
} from '../types'
import { FORMAT_LABELS, MODE_LABELS, PROCESSING_MODE_LABELS } from '../types'

interface ProcessOptionsPanelProps {
  value: ProcessOptions
  onChange: (next: ProcessOptions) => void
  disabled?: boolean
}

export function ProcessOptionsPanel({ value, onChange, disabled }: ProcessOptionsPanelProps) {
  const set = <K extends keyof ProcessOptions>(key: K, v: ProcessOptions[K]) => {
    onChange({ ...value, [key]: v })
  }

  const toggleFormat = (fmt: ClipFormat) => {
    const has = value.formats.includes(fmt)
    if (has && value.formats.length === 1) return
    set(
      'formats',
      has ? value.formats.filter((f) => f !== fmt) : [...value.formats, fmt],
    )
  }

  const showInterview = value.content_mode === 'interview' || value.content_mode === 'multi_speaker'
  const isFullSplit = value.processing_mode === 'full_split'

  return (
    <section className="rounded-2xl border border-white/8 bg-white/[0.03] p-4 sm:p-5">
      <div className="mb-5">
        <h3 className="font-display text-base text-white">Opciones de procesamiento</h3>
        <p className="mt-1 text-xs text-slate-500">
          Configura el clip y mira la vista previa a la derecha en tiempo real.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-5">
          <fieldset disabled={disabled} className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Modo de procesamiento
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {(Object.keys(PROCESSING_MODE_LABELS) as ProcessingMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => set('processing_mode', mode)}
                  className={[
                    'rounded-xl border px-3 py-3 text-left text-sm transition',
                    value.processing_mode === mode
                      ? 'border-violet-400/50 bg-violet-400/10 text-white'
                      : 'border-white/8 bg-black/20 text-slate-400 hover:border-white/20',
                  ].join(' ')}
                >
                  {PROCESSING_MODE_LABELS[mode]}
                </button>
              ))}
            </div>
            {isFullSplit && (
              <p className="text-[11px] leading-relaxed text-slate-500">
                Divide todo el video en partes consecutivas. Conserva formatos, subtítulos y recorte.
              </p>
            )}
          </fieldset>

          {isFullSplit && (
            <fieldset disabled={disabled} className="space-y-3">
              <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
                División del video
              </legend>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ['by_duration', 'Por duración (segundos)'],
                    ['by_count', 'Por cantidad de partes'],
                  ] as [SplitStrategy, string][]
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => set('split_strategy', id)}
                    className={[
                      'rounded-lg border px-3 py-1.5 text-xs transition',
                      value.split_strategy === id
                        ? 'border-violet-400/50 bg-violet-400/10 text-violet-200'
                        : 'border-white/8 text-slate-400 hover:border-white/20',
                    ].join(' ')}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {value.split_strategy === 'by_duration' ? (
                <NumberField
                  label="Segundos por parte"
                  value={value.split_part_duration}
                  min={10}
                  max={600}
                  disabled={disabled}
                  onChange={(n) => set('split_part_duration', n)}
                />
              ) : (
                <NumberField
                  label="Número de partes"
                  value={value.split_part_count}
                  min={2}
                  max={50}
                  disabled={disabled}
                  onChange={(n) => set('split_part_count', n)}
                />
              )}
            </fieldset>
          )}

          <fieldset disabled={disabled} className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Tipo de contenido
            </legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {(Object.keys(MODE_LABELS) as ContentMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => set('content_mode', mode)}
                  className={[
                    'rounded-xl border px-3 py-3 text-left text-sm transition',
                    value.content_mode === mode
                      ? 'border-cyan-400/50 bg-cyan-400/10 text-white'
                      : 'border-white/8 bg-black/20 text-slate-400 hover:border-white/20',
                  ].join(' ')}
                >
                  {MODE_LABELS[mode]}
                </button>
              ))}
            </div>
          </fieldset>

          {showInterview && (
            <fieldset disabled={disabled} className="space-y-2">
              <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Layout de entrevista (vertical)
              </legend>
              <div className="grid gap-2 sm:grid-cols-3">
                {(
                  [
                    ['split_stack', 'Split fijo', 'Una persona arriba, otra abajo'],
                    ['active_focus', 'Dinámico', 'Quien habla pasa arriba'],
                    ['single_follow', 'Solo hablante', 'Recorta a quien habla'],
                  ] as [InterviewLayout, string, string][]
                ).map(([id, title, desc]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => set('interview_layout', id)}
                    className={[
                      'rounded-xl border px-3 py-3 text-left transition',
                      value.interview_layout === id
                        ? 'border-teal-400/50 bg-teal-400/10'
                        : 'border-white/8 bg-black/20 hover:border-white/20',
                    ].join(' ')}
                  >
                    <div className="text-sm text-white">{title}</div>
                    <div className="mt-0.5 text-[11px] text-slate-500">{desc}</div>
                  </button>
                ))}
              </div>
            </fieldset>
          )}

          <fieldset disabled={disabled} className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Formatos de clip
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {(Object.keys(FORMAT_LABELS) as ClipFormat[]).map((fmt) => {
                const on = value.formats.includes(fmt)
                return (
                  <label
                    key={fmt}
                    className={[
                      'flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-3 text-sm transition',
                      on
                        ? 'border-cyan-400/40 bg-cyan-400/8 text-white'
                        : 'border-white/8 bg-black/20 text-slate-400 hover:border-white/20',
                    ].join(' ')}
                  >
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggleFormat(fmt)}
                      className="accent-cyan-400"
                    />
                    {FORMAT_LABELS[fmt]}
                  </label>
                )
              })}
            </div>
          </fieldset>

          <fieldset disabled={disabled} className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Recorte / relleno
            </legend>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ['smart_crop', 'Recorte inteligente'],
                  ['blur_bg', 'Fondo difuminado'],
                  ['letterbox', 'Barras negras'],
                ] as [FillMode, string][]
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => set('fill_mode', id)}
                  className={[
                    'rounded-lg border px-3 py-1.5 text-xs transition',
                    value.fill_mode === id
                      ? 'border-cyan-400/50 bg-cyan-400/10 text-cyan-200'
                      : 'border-white/8 text-slate-400 hover:border-white/20',
                  ].join(' ')}
                >
                  {label}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset disabled={disabled} className="space-y-2">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Video
            </legend>
            <Toggle
              label="Modo espejo (voltear horizontalmente)"
              checked={value.mirror_horizontal}
              onChange={(v) => set('mirror_horizontal', v)}
            />
          </fieldset>

          {!isFullSplit && (
          <div className="grid gap-4 sm:grid-cols-3">
            <NumberField label="Máx. clips" value={value.max_clips} min={1} max={20} disabled={disabled} onChange={(n) => set('max_clips', n)} />
            <NumberField label="Duración mín. (s)" value={value.min_clip_duration} min={5} max={120} disabled={disabled} onChange={(n) => set('min_clip_duration', n)} />
            <NumberField label="Duración máx. (s)" value={value.max_clip_duration} min={10} max={180} disabled={disabled} onChange={(n) => set('max_clip_duration', n)} />
          </div>
          )}

          <fieldset disabled={disabled} className="space-y-3">
            <legend className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Estilo de subtítulos
            </legend>
            <div className="flex flex-wrap gap-4 text-sm text-slate-300">
              <Toggle label="Incrustar en video" checked={value.burn_subtitles} onChange={(v) => set('burn_subtitles', v)} />
              <Toggle label="Exportar SRT" checked={value.export_srt} onChange={(v) => set('export_srt', v)} />
              <Toggle label="Exportar VTT" checked={value.export_vtt} onChange={(v) => set('export_vtt', v)} />
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  ['clean', 'Limpio', 'Contorno fino, sin caja'],
                  ['social', 'Redes / interactivo', 'Palabra activa en color'],
                  ['karaoke', 'Karaoke', 'Resalta al ritmo'],
                  ['subtle', 'Discreto', 'Pequeño, sin fondo'],
                  ['boxed', 'Con fondo', 'Caja semitransparente'],
                ] as [SubtitleStyle, string, string][]
              ).map(([id, title, desc]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => set('subtitle_style', id)}
                  className={[
                    'rounded-xl border px-3 py-3 text-left transition',
                    value.subtitle_style === id
                      ? 'border-teal-400/50 bg-teal-400/10'
                      : 'border-white/8 bg-black/20 hover:border-white/20',
                  ].join(' ')}
                >
                  <div className="text-sm text-white">{title}</div>
                  <div className="mt-0.5 text-[11px] leading-snug text-slate-500">{desc}</div>
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-end gap-4">
              <div className="space-y-1.5">
                <span className="text-xs text-slate-500">Posición</span>
                <div className="flex gap-2">
                  {(
                    [
                      ['top', 'Arriba'],
                      ['center', 'Centro'],
                      ['bottom', 'Abajo'],
                    ] as [SubtitlePosition, string][]
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => set('subtitle_position', id)}
                      className={[
                        'rounded-lg border px-3 py-1.5 text-xs transition',
                        value.subtitle_position === id
                          ? 'border-cyan-400/50 bg-cyan-400/10 text-cyan-200'
                          : 'border-white/8 text-slate-400 hover:border-white/20',
                      ].join(' ')}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <label className="block min-w-[160px] flex-1 space-y-1.5">
                <span className="text-xs text-slate-500">
                  Tamaño ({value.subtitle_size}
                  {value.subtitle_size < 18
                    ? ' · pequeño'
                    : value.subtitle_size < 28
                      ? ' · medio'
                      : value.subtitle_size < 38
                        ? ' · grande'
                        : ' · enorme'}
                  )
                </span>
                <input
                  type="range"
                  min={12}
                  max={48}
                  value={value.subtitle_size}
                  onChange={(e) => set('subtitle_size', Number(e.target.value))}
                  className="w-full accent-cyan-400"
                />
                <p className="text-[10px] text-slate-600">
                  Se adapta al formato (ej. 9:16 1080×1920). 32 ≈ tipografía grande tipo Reels.
                </p>
              </label>
            </div>
          </fieldset>

          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs font-medium uppercase tracking-wider text-slate-500">Idioma Whisper</label>
            <select
              disabled={disabled}
              value={value.language ?? ''}
              onChange={(e) => set('language', e.target.value || null)}
              className="rounded-lg border border-white/10 bg-[#12151e] px-3 py-1.5 text-sm text-white"
            >
              <option value="">Auto-detectar</option>
              <option value="es">Español</option>
              <option value="en">English</option>
              <option value="pt">Português</option>
              <option value="fr">Français</option>
            </select>
          </div>
        </div>

        <div className="lg:sticky lg:top-24 lg:self-start">
          <ClipPreview options={value} />
        </div>
      </div>
    </section>
  )
}

function NumberField({
  label, value, min, max, onChange, disabled,
}: {
  label: string; value: number; min: number; max: number; onChange: (n: number) => void; disabled?: boolean
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs text-slate-500">{label}</span>
      <input
        type="number" min={min} max={max} disabled={disabled} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-lg border border-white/10 bg-[#12151e] px-3 py-2 text-sm text-white"
      />
    </label>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="accent-cyan-400" />
      {label}
    </label>
  )
}
