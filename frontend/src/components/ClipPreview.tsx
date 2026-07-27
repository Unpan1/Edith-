import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import type { ClipFormat, ProcessOptions } from '../types'
import { FORMAT_LABELS } from '../types'

const SAMPLE_WORDS = ['Este', 'es', 'un', 'momento', 'clave', 'de', 'la', 'entrevista']

const ASPECT: Record<ClipFormat, string> = {
  vertical_9_16: '9 / 16',
  portrait_4_5: '4 / 5',
  square_1_1: '1 / 1',
  landscape_16_9: '16 / 9',
}

interface ClipPreviewProps {
  options: ProcessOptions
}

export function ClipPreview({ options }: ClipPreviewProps) {
  const formats = options.formats.length ? options.formats : (['vertical_9_16'] as ClipFormat[])
  const [previewFormat, setPreviewFormat] = useState<ClipFormat>(formats[0])
  const [activeWord, setActiveWord] = useState(0)

  useEffect(() => {
    if (!formats.includes(previewFormat)) {
      setPreviewFormat(formats[0])
    }
  }, [formats, previewFormat])

  // Animación karaoke / social
  useEffect(() => {
    if (options.subtitle_style !== 'karaoke' && options.subtitle_style !== 'social') {
      return
    }
    const id = window.setInterval(() => {
      setActiveWord((w) => (w + 1) % SAMPLE_WORDS.length)
    }, 450)
    return () => window.clearInterval(id)
  }, [options.subtitle_style])

  const isInterview =
    (options.content_mode === 'interview' || options.content_mode === 'multi_speaker') &&
    (previewFormat === 'vertical_9_16' || previewFormat === 'portrait_4_5') &&
    options.interview_layout !== 'single_follow'

  const isVertical =
    previewFormat === 'vertical_9_16' || previewFormat === 'portrait_4_5'

  const frameMaxH = isVertical ? 420 : 260
  const frameMaxW = isVertical ? 240 : 420

  const subtitleBlock = useMemo(() => {
    if (!options.burn_subtitles) return null

        const sizePx = Math.round(10 + ((options.subtitle_size - 12) / 36) * 18)
    const baseStyle: CSSProperties = {
      fontSize: `${sizePx}px`,
      lineHeight: 1.25,
      textAlign: 'center',
      maxWidth: '92%',
      pointerEvents: 'none',
    }

    let content: ReactNode
    if (options.subtitle_style === 'karaoke' || options.subtitle_style === 'social') {
      const start = Math.max(0, activeWord - 1)
      const chunk = SAMPLE_WORDS.slice(start, start + 4)
      content = (
        <span style={{ fontWeight: 800, letterSpacing: '0.01em' }}>
          {chunk.map((word, i) => {
            const globalIdx = start + i
            const active = globalIdx === activeWord
            return (
              <span
                key={`${word}-${i}`}
                style={{
                  color: active ? '#ffe500' : '#fff',
                  textShadow: active
                    ? '0 0 8px rgba(255,229,0,0.45), 0 1px 2px #000, 0 0 1px #000, 1px 1px 0 #000'
                    : '0 1px 2px #000, 0 0 1px #000, 1px 1px 0 #000, -1px -1px 0 #000',
                  marginRight: 6,
                  transition: 'color 0.15s ease',
                }}
              >
                {word}
              </span>
            )
          })}
        </span>
      )
    } else if (options.subtitle_style === 'boxed') {
      content = (
        <span
          style={{
            ...baseStyle,
            display: 'inline-block',
            background: 'rgba(0,0,0,0.72)',
            color: '#fff',
            padding: '4px 10px',
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          Este es un momento clave
        </span>
      )
    } else if (options.subtitle_style === 'subtle') {
      content = (
        <span
          style={{
            color: 'rgba(240,240,240,0.92)',
            fontWeight: 500,
            textShadow: '0 1px 2px #000',
            fontSize: `${Math.min(sizePx, 14)}px`,
          }}
        >
          Este es un momento clave
        </span>
      )
    } else {
      content = (
        <span
          style={{
            color: '#fff',
            fontWeight: 700,
            textShadow:
              '0 1px 2px #000, 0 0 1px #000, 1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000',
          }}
        >
          Este es un momento clave
        </span>
      )
    }

    const positionClass =
      options.subtitle_position === 'top'
        ? 'items-start pt-[12%]'
        : options.subtitle_position === 'bottom'
          ? 'items-end pb-[10%]'
          : 'items-center'

    return (
      <div
        className={`pointer-events-none absolute inset-0 z-20 flex justify-center ${positionClass}`}
        style={baseStyle}
      >
        {content}
      </div>
    )
  }, [
    options.burn_subtitles,
    options.subtitle_style,
    options.subtitle_size,
    options.subtitle_position,
    activeWord,
  ])

  return (
    <aside className="flex flex-col items-center gap-3 rounded-2xl border border-white/8 bg-[#0d1018] p-4">
      <div className="w-full space-y-1">
        <h4 className="text-xs font-medium uppercase tracking-wider text-slate-500">
          Vista previa
        </h4>
        <p className="text-[11px] text-slate-500">
          Se actualiza con tus opciones (formato, subtítulos, relleno…).
        </p>
      </div>

      {formats.length > 1 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {formats.map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => setPreviewFormat(fmt)}
              className={[
                'rounded-md border px-2 py-1 text-[10px] transition',
                previewFormat === fmt
                  ? 'border-cyan-400/50 bg-cyan-400/10 text-cyan-200'
                  : 'border-white/10 text-slate-500 hover:border-white/20',
              ].join(' ')}
            >
              {fmt.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      )}

      <div
        className="relative overflow-hidden rounded-xl border border-white/15 shadow-2xl shadow-black/50 transition-all duration-300"
        style={{
          aspectRatio: ASPECT[previewFormat],
          width: '100%',
          maxWidth: frameMaxW,
          maxHeight: frameMaxH,
        }}
      >
        <div
          className="absolute inset-0"
          style={options.mirror_horizontal ? { transform: 'scaleX(-1)' } : undefined}
        >
          {/* Fondo según fill_mode */}
          <PreviewBackground fillMode={options.fill_mode} isInterview={isInterview} />

          {/* Contenido / hablantes */}
          {isInterview ? (
            <InterviewLayers layout={options.interview_layout} />
          ) : (
            <MonologueLayer fillMode={options.fill_mode} />
          )}
        </div>

        {subtitleBlock}

        {/* Badge formato */}
        <div className="absolute top-2 left-2 z-30 rounded bg-black/60 px-1.5 py-0.5 text-[9px] text-slate-300">
          {FORMAT_LABELS[previewFormat].split('·')[0].trim()}
        </div>
        {options.mirror_horizontal && (
          <div className="absolute top-2 right-2 z-30 rounded bg-violet-500/30 px-1.5 py-0.5 text-[9px] text-violet-100">
            Espejo
          </div>
        )}
      </div>

      <ul className="w-full space-y-1 text-[11px] text-slate-500">
        <li>
          Proceso:{' '}
          <span className="text-slate-300">
            {options.processing_mode === 'full_split' ? 'Dividir video completo' : 'Clips IA'}
          </span>
        </li>
        <li>
          Modo:{' '}
          <span className="text-slate-300">
            {options.content_mode === 'interview'
              ? 'Entrevista'
              : options.content_mode === 'multi_speaker'
                ? 'Varias personas'
                : 'Monólogo'}
          </span>
        </li>
        <li>
          Relleno:{' '}
          <span className="text-slate-300">
            {options.fill_mode === 'blur_bg'
              ? 'Fondo difuminado'
              : options.fill_mode === 'letterbox'
                ? 'Barras negras'
                : 'Recorte inteligente'}
          </span>
        </li>
        <li>
          Subtítulos:{' '}
          <span className="text-slate-300">
            {options.burn_subtitles
              ? `${options.subtitle_style} · ${options.subtitle_position} · ${options.subtitle_size}px`
              : 'Desactivados'}
          </span>
        </li>
      </ul>
    </aside>
  )
}

function PreviewBackground({
  fillMode,
  isInterview,
}: {
  fillMode: ProcessOptions['fill_mode']
  isInterview: boolean
}) {
  if (fillMode === 'letterbox' && !isInterview) {
    return <div className="absolute inset-0 bg-black" />
  }
  if (fillMode === 'blur_bg') {
    return (
      <div
        className="absolute inset-0 scale-110 bg-cover bg-center blur-md brightness-75"
        style={{
          backgroundImage:
            'linear-gradient(135deg, #1e3a4c 0%, #0f766e 40%, #164e63 100%)',
        }}
      />
    )
  }
  return (
    <div className="absolute inset-0 bg-gradient-to-br from-slate-800 via-slate-900 to-[#0a0c10]" />
  )
}

function MonologueLayer({ fillMode }: { fillMode: ProcessOptions['fill_mode'] }) {
  const letterbox = fillMode === 'letterbox'
  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center">
      {letterbox && (
        <>
          <div className="absolute inset-x-0 top-0 h-[18%] bg-black" />
          <div className="absolute inset-x-0 bottom-0 h-[18%] bg-black" />
        </>
      )}
      <div
        className={[
          'relative flex flex-col items-center justify-end overflow-hidden rounded-lg',
          letterbox ? 'h-[64%] w-[72%]' : fillMode === 'blur_bg' ? 'h-[78%] w-[70%]' : 'h-full w-full',
        ].join(' ')}
        style={{
          background:
            'linear-gradient(180deg, #334155 0%, #1e293b 45%, #0f172a 100%)',
        }}
      >
        <PersonSilhouette className="mb-[-4%] h-[70%] w-[55%]" tone="a" />
      </div>
    </div>
  )
}

function InterviewLayers({ layout }: { layout: ProcessOptions['interview_layout'] }) {
  const focus = layout === 'active_focus'
  return (
    <div className="absolute inset-0 z-10 flex flex-col">
      <div className="relative flex flex-1 items-end justify-center overflow-hidden border-b border-white/10 bg-gradient-to-b from-slate-600 to-slate-800">
        <PersonSilhouette
          className={`mb-[-6%] ${focus ? 'h-[85%] w-[70%]' : 'h-[75%] w-[60%]'}`}
          tone="a"
        />
        <span className="absolute top-2 right-2 rounded bg-black/50 px-1.5 py-0.5 text-[8px] text-white/70">
          Hablante A
        </span>
      </div>
      <div className="relative flex flex-1 items-end justify-center overflow-hidden bg-gradient-to-b from-teal-900/80 to-slate-900">
        <PersonSilhouette
          className="mb-[-6%] h-[75%] w-[60%]"
          tone="b"
        />
        <span className="absolute top-2 right-2 rounded bg-black/50 px-1.5 py-0.5 text-[8px] text-white/70">
          Hablante B
        </span>
      </div>
    </div>
  )
}

function PersonSilhouette({
  className,
  tone,
}: {
  className?: string
  tone: 'a' | 'b'
}) {
  const fill = tone === 'a' ? '#94a3b8' : '#5eead4'
  return (
    <svg viewBox="0 0 120 160" className={className} aria-hidden>
      <circle cx="60" cy="42" r="28" fill={fill} opacity="0.85" />
      <ellipse cx="60" cy="120" rx="42" ry="48" fill={fill} opacity="0.7" />
    </svg>
  )
}
