export type VideoStatus =
  | 'uploaded'
  | 'extracting_audio'
  | 'transcribing'
  | 'analyzing'
  | 'generating_clips'
  | 'adding_subtitles'
  | 'completed'
  | 'failed'

export type ContentMode = 'monologue' | 'interview' | 'multi_speaker'
export type ProcessingMode = 'highlights' | 'full_split'
export type SplitStrategy = 'by_count' | 'by_duration'
export type ClipFormat = 'vertical_9_16' | 'portrait_4_5' | 'square_1_1' | 'landscape_16_9'
export type FillMode = 'smart_crop' | 'blur_bg' | 'letterbox'
export type InterviewLayout = 'split_stack' | 'active_focus' | 'single_follow'
export type SubtitleStyle = 'clean' | 'social' | 'karaoke' | 'boxed' | 'subtle'
export type SubtitlePosition = 'bottom' | 'center' | 'top'

export interface ProcessOptions {
  processing_mode: ProcessingMode
  split_strategy: SplitStrategy
  split_part_count: number
  split_part_duration: number
  mirror_horizontal: boolean
  content_mode: ContentMode
  formats: ClipFormat[]
  fill_mode: FillMode
  interview_layout: InterviewLayout
  burn_subtitles: boolean
  subtitle_style: SubtitleStyle
  subtitle_position: SubtitlePosition
  subtitle_size: number
  export_srt: boolean
  export_vtt: boolean
  max_clips: number
  min_clip_duration: number
  max_clip_duration: number
  language: string | null
}

export interface Video {
  id: number
  nombre_original: string
  ruta_archivo?: string
  duracion: number | null
  tamano: number | null
  estado: VideoStatus
  progreso: number
  mensaje_error: string | null
  progreso_detalle?: string | null
  eta_segundos?: number | null
  opciones?: ProcessOptions | null
  fecha_subida: string
  clips?: Clip[]
}

export interface Clip {
  id: number
  video_id: number
  inicio: number
  fin: number
  duracion: number
  ruta_clip: string
  ruta_miniatura: string | null
  ruta_srt: string | null
  ruta_vtt: string | null
  titulo_generado: string | null
  formato: string | null
  score: number
  fecha: string
}

export interface ProcessResponse {
  video_id: number
  message: string
  estado: VideoStatus
  opciones?: ProcessOptions
}

export const DEFAULT_OPTIONS: ProcessOptions = {
  processing_mode: 'highlights',
  split_strategy: 'by_duration',
  split_part_count: 4,
  split_part_duration: 60,
  mirror_horizontal: false,
  content_mode: 'monologue',
  formats: ['vertical_9_16'],
  fill_mode: 'smart_crop',
  interview_layout: 'split_stack',
  burn_subtitles: true,
  subtitle_style: 'clean',
  subtitle_position: 'center',
  subtitle_size: 24,
  export_srt: true,
  export_vtt: true,
  max_clips: 6,
  min_clip_duration: 20,
  max_clip_duration: 60,
  language: null,
}

export const STATUS_LABELS: Record<VideoStatus, string> = {
  uploaded: 'Subido',
  extracting_audio: 'Extrayendo audio',
  transcribing: 'Transcribiendo',
  analyzing: 'Analizando',
  generating_clips: 'Generando clips',
  adding_subtitles: 'Agregando subtítulos',
  completed: 'Finalizado',
  failed: 'Error',
}

export const ACTIVE_STATUSES: VideoStatus[] = [
  'extracting_audio',
  'transcribing',
  'analyzing',
  'generating_clips',
  'adding_subtitles',
]

export const FORMAT_LABELS: Record<ClipFormat, string> = {
  vertical_9_16: 'Vertical 9:16 · TikTok / Reels / Shorts',
  portrait_4_5: 'Vertical 4:5 · Instagram Feed',
  square_1_1: 'Cuadrado 1:1 · Feed / Facebook',
  landscape_16_9: 'Horizontal 16:9 · YouTube',
}

export const MODE_LABELS: Record<ContentMode, string> = {
  monologue: 'Una persona (monólogo)',
  interview: 'Entrevista (2 personas)',
  multi_speaker: 'Varias personas',
}

export const PROCESSING_MODE_LABELS: Record<ProcessingMode, string> = {
  highlights: 'Clips IA (mejores momentos)',
  full_split: 'Dividir video completo',
}
