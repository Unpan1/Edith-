export function Header() {
  return (
    <header className="border-b border-white/8 bg-[#0c0e14]/80 backdrop-blur-xl sticky top-0 z-40">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-teal-600 shadow-lg shadow-cyan-500/20">
            <svg viewBox="0 0 24 24" className="h-5 w-5 text-[#0a0c10]" fill="currentColor">
              <path d="M4 6a2 2 0 012-2h6l2 2h6a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm8 2.5v7l5.5-3.5L12 8.5z" />
            </svg>
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold tracking-tight text-white">
              ClipAI Studio
            </h1>
            <p className="text-[11px] tracking-wide text-slate-500 uppercase">
              Clips automáticos con IA
            </p>
          </div>
        </div>
        <span className="hidden rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-400 sm:inline">
          Local · Whisper · FFmpeg
        </span>
      </div>
    </header>
  )
}
