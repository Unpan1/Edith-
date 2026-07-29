import type { Clip, ClipFormat } from '../types'
import { api } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export interface CropBoxNorm {
  x: number
  y: number
  w: number
  h: number
}

export interface ComposeSourceInfo {
  id: number
  nombre_original: string
  duracion: number | null
  width: number
  height: number
  stream_url: string
}

export interface ComposeSplitPayload {
  video_id: number
  format: ClipFormat
  start: number
  end: number
  top: CropBoxNorm
  bottom: CropBoxNorm
  mirror_horizontal?: boolean
  title?: string
}

export interface ComposeJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds: number | null
  error: string | null
  clip_id: number | null
  clip?: Clip | null
}

export function composeStreamUrl(videoId: number): string {
  return `${API_URL}/compose/videos/${videoId}/stream`
}

export async function getComposeSource(videoId: number): Promise<ComposeSourceInfo> {
  const { data } = await api.get<ComposeSourceInfo>(`/compose/videos/${videoId}/source`)
  return data
}

export async function startComposeSplit(
  payload: ComposeSplitPayload,
): Promise<{ job_id: string }> {
  const { data } = await api.post<{ job_id: string }>('/compose/split', payload)
  return data
}

export async function getComposeJob(jobId: string): Promise<ComposeJobStatus> {
  const { data } = await api.get<ComposeJobStatus>(`/compose/jobs/${jobId}`)
  return data
}
