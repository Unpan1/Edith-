import { useCallback, useRef, useState } from 'react'

interface DropZoneProps {
  onFile: (file: File) => void
  disabled?: boolean
}

const ACCEPT = '.mp4,.mov,.avi,.mkv,.webm,video/mp4,video/quicktime,video/x-msvideo,video/webm'

export function DropZone({ onFile, disabled }: DropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files?.length || disabled) return
      onFile(files[0])
    },
    [onFile, disabled],
  )

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
      }}
      onDragEnter={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        handleFiles(e.dataTransfer.files)
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={[
        'group relative cursor-pointer overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300',
        dragging
          ? 'border-cyan-400 bg-cyan-400/10 scale-[1.01]'
          : 'border-white/12 bg-white/[0.03] hover:border-cyan-400/40 hover:bg-white/[0.05]',
        disabled ? 'pointer-events-none opacity-50' : '',
      ].join(' ')}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.08),transparent_70%)]" />
      <div className="relative flex flex-col items-center gap-3 px-6 py-14 text-center sm:py-16">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400/20 to-teal-600/20 ring-1 ring-cyan-400/30 transition group-hover:scale-105">
          <svg className="h-7 w-7 text-cyan-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        <div>
          <p className="font-display text-lg text-white">
            Arrastra tu video aquí
          </p>
          <p className="mt-1 text-sm text-slate-400">
            o haz clic para seleccionar · MP4, MOV, MKV, WEBM
          </p>
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}
