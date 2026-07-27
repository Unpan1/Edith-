export type Platform =
  | 'youtube'
  | 'tiktok'
  | 'instagram'
  | 'shorts'
  | 'facebook'
  | 'linkedin'
  | 'x'

export type PostStatus = 'draft' | 'scheduled' | 'published' | 'failed'

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'retry'

export interface RecentClipItem {
  id: number
  titulo: string | null
  duracion: number
  score: number
  formato: string | null
  fecha: string | null
}

export interface DashboardStats {
  videos: number
  videos_completed: number
  clips: number
  minutes_processed: number
  time_saved_hours: number
  jobs_queued: number
  jobs_processing: number
  scheduled_posts: number
  published_posts: number
  credits_balance: number
  credits_used_month: number
  notifications_unread: number
  recent_clips: RecentClipItem[]
}

export interface LibraryVideoItem {
  id: number
  nombre_original: string
  duracion: number | null
  estado: string
  progreso: number
  fecha_subida: string
  clips_count: number
}

export interface LibraryClipItem {
  id: number
  video_id: number
  titulo_generado: string | null
  duracion: number
  score: number
  formato: string | null
  ruta_clip: string
  ruta_miniatura: string | null
  fecha: string
}

export interface LibraryResponse {
  videos: LibraryVideoItem[]
  clips: LibraryClipItem[]
}

export interface ClipContent {
  id: number
  clip_id: number
  titles: string[]
  descriptions: string[]
  hashtags: string[]
  cta: string | null
  seo_keywords: string[]
}

export interface Thumbnail {
  id: number
  clip_id: number
  ruta: string
  texto_overlay: string | null
  es_principal: boolean
}

export interface ClipEditor {
  clip_id: number
  titulo_generado: string | null
  inicio: number
  fin: number
  duracion: number
  formato: string | null
  ruta_clip: string
  ruta_miniatura: string | null
  caption_texto: string | null
  caption_estilo: string | null
  caption_idioma: string | null
}

export interface ClipEditorUpdate {
  titulo_generado?: string | null
  caption_texto?: string | null
  caption_estilo?: string | null
  caption_idioma?: string | null
}

export interface ScheduledPost {
  id: number
  user_id: number
  clip_id: number | null
  platform: Platform
  status: PostStatus
  titulo: string | null
  descripcion: string | null
  hashtags: string[] | null
  scheduled_at: string | null
  published_at: string | null
  error_message: string | null
  fecha: string
}

export interface ScheduledPostCreate {
  clip_id?: number | null
  platform: Platform
  status?: PostStatus
  titulo?: string | null
  descripcion?: string | null
  hashtags?: string[] | null
  scheduled_at?: string | null
}

export interface SocialAccount {
  id: number
  user_id: number
  platform: Platform
  handle: string | null
  connected: boolean
}

export interface CalendarMonth {
  year: number
  month: number
  posts: ScheduledPost[]
}

export interface AnalyticsSnapshot {
  id: number
  user_id: number
  clip_id: number | null
  video_id: number | null
  platform: Platform | null
  views: number
  likes: number
  comments: number
  shares: number
  watch_time_sec: number
  fecha: string
}

export interface RankingItem {
  clip_id: number | null
  video_id: number | null
  score: number
  views: number
  likes: number
}

export interface RankingResponse {
  items: RankingItem[]
}

export interface LearningInsight {
  id: number
  user_id: number
  clip_id: number | null
  insight_type: string
  titulo: string
  detalle: string
  score: number
  fecha: string
}

export interface AutomationSettings {
  user_id: number
  enrich_after_process: boolean
  auto_schedule_stubs: boolean
  auto_thumbnails: boolean
  default_platforms: string[] | null
}

export interface AutomationSettingsUpdate {
  enrich_after_process?: boolean
  auto_schedule_stubs?: boolean
  auto_thumbnails?: boolean
  default_platforms?: string[] | null
}

export interface Plan {
  id: number
  nombre: string
  credits_monthly: number
  price: number
  features: unknown
  activo: boolean
}

export interface CreditLedger {
  id: number
  user_id: number
  delta: number
  reason: string
  balance_after: number
  fecha: string
}

export interface CreditsBalance {
  user_id: number
  balance: number
  plan: Plan | null
  ledger: CreditLedger[]
}

export interface AdminOverview {
  stats: {
    users: number
    videos: number
    clips: number
    jobs: number
    scheduled_posts: number
    plans: number
  }
  users: Array<{ id: number; nombre: string; email: string }>
  recent_jobs: Array<{
    id: number
    tipo: string
    status: string
    attempts: number
    error: unknown
  }>
}

export interface TrendReport {
  id: number
  category: string
  country: string
  title: string
  score: number
  opportunity_score: number
  data: unknown
  fecha: string
}

export interface TrendsResponse {
  items: TrendReport[]
}

export interface Job {
  id: number
  user_id: number | null
  tipo: string
  payload: unknown
  status: JobStatus
  attempts: number
  max_attempts: number
  result: unknown
  error: string | null
  created_at: string
  updated_at: string
}

export interface GrowthPlanRequest {
  instruction: string
  video_id: number
}

export interface GrowthEnqueueResponse {
  job_id: number
  message: string
}

export interface Project {
  id: number
  user_id: number
  nombre: string
  descripcion: string | null
  fecha_creacion: string
}

export interface ProjectCreate {
  nombre: string
  descripcion?: string | null
}

export const PLATFORM_LABELS: Record<Platform, string> = {
  youtube: 'YouTube',
  tiktok: 'TikTok',
  instagram: 'Instagram',
  shorts: 'Shorts',
  facebook: 'Facebook',
  linkedin: 'LinkedIn',
  x: 'X',
}

export const POST_STATUS_LABELS: Record<PostStatus, string> = {
  draft: 'Borrador',
  scheduled: 'Programado',
  published: 'Publicado',
  failed: 'Fallido',
}
