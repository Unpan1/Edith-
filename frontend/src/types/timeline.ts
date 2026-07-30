export type TimelineClipKind = 'video' | 'image' | 'audio' | 'title'

export type TrackKind = 'video' | 'title' | 'audio'

export interface TimelineClip {
  id: string
  kind: TimelineClipKind
  assetId?: string
  trackId: string
  start: number
  duration: number
  /** Offset dentro del archivo fuente (tras cortar) */
  sourceOffset: number
  volume: number
  label: string
  text?: string
  fontFamily?: string
  fontSize?: number
  color?: string
  xPercent?: number
  yPercent?: number
}

export interface TimelineTrack {
  id: string
  kind: TrackKind
  name: string
}

export const FONT_OPTIONS = [
  'Arial',
  'Arial Black',
  'Times New Roman',
  'Courier New',
  'Verdana',
  'Comic Sans MS',
  'Impact',
  'Georgia',
  'Trebuchet MS',
  'Segoe UI',
] as const

export const DEFAULT_TRACKS: TimelineTrack[] = [
  { id: 'V1', kind: 'video', name: 'Video 1' },
  { id: 'T1', kind: 'title', name: 'Títulos' },
  { id: 'A1', kind: 'audio', name: 'Audio 1' },
  { id: 'A2', kind: 'audio', name: 'Audio 2' },
]

export function uid(prefix = 'c'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

export function formatTime(sec: number): string {
  const s = Math.max(0, sec)
  const m = Math.floor(s / 60)
  const r = s - m * 60
  return `${m}:${r.toFixed(1).padStart(4, '0')}`
}

export function projectDuration(clips: TimelineClip[]): number {
  if (!clips.length) return 10
  return Math.max(10, ...clips.map((c) => c.start + c.duration))
}
