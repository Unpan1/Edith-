import { useState } from 'react'

interface YoutubeImportProps {
  onSubmit: (url: string) => void
  disabled?: boolean
  loading?: boolean
}

export function YoutubeImport({ onSubmit, disabled, loading }: YoutubeImportProps) {
  const [url, setUrl] = useState('')

  const canSubmit = !disabled && !loading && url.trim().length > 10

  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className="mb-3 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-500/15 ring-1 ring-rose-400/25">
          <svg className="h-5 w-5 text-rose-300" viewBox="0 0 24 24" fill="currentColor">
            <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.5 31.5 0 0 0 0 12a31.5 31.5 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.5 31.5 0 0 0 24 12a31.5 31.5 0 0 0-.5-5.8zM9.75 15.5v-7l6.2 3.5-6.2 3.5z" />
          </svg>
        </div>
        <div>
          <h3 className="text-sm font-medium text-white">Importar desde YouTube</h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Pega un link público. Se descarga en local con yt-dlp (gratis, sin APIs de pago).
          </p>
        </div>
      </div>

      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault()
          if (!canSubmit) return
          onSubmit(url.trim())
        }}
      >
        <input
          type="url"
          value={url}
          disabled={disabled || loading}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=… o youtu.be/…"
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-[#12151e] px-3 py-2.5 text-sm text-white placeholder:text-slate-600 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-rose-500/90 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-rose-500 disabled:opacity-40"
        >
          {loading ? 'Descargando…' : 'Importar'}
        </button>
      </form>
    </div>
  )
}
