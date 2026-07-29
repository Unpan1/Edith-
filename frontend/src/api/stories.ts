import { api } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export type StoryPreset =
  | 'narracion'
  | 'misterio'
  | 'motivacional'
  | 'terror'
  | 'documental'
  | 'humor'

export type StoryFormat = '9:16' | '16:9' | '1:1'

export interface StoryPresetInfo {
  id: string
  label: string
  description: string
}

export interface StoryOptions {
  presets: StoryPresetInfo[]
  formats: string[]
  note: string
}

export interface StoryGenerateBody {
  story: string
  preset: StoryPreset
  instructions?: string
  format: StoryFormat
  voice_id: string
  mood: string
  language?: string
}

export interface StoryJobStart {
  job_id: string
}

export interface StoryJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds?: number | null
  error?: string | null
  filename?: string | null
  stream_url?: string | null
  download_url?: string | null
  scenes_count?: number | null
  duration_seconds?: number | null
  preset?: string | null
  format?: string | null
}

export async function getStoryOptions(): Promise<StoryOptions> {
  const { data } = await api.get<StoryOptions>('/stories/options')
  return data
}

export async function startStoryGenerate(
  payload: StoryGenerateBody,
): Promise<StoryJobStart> {
  const { data } = await api.post<StoryJobStart>('/stories/generate', payload, {
    timeout: 30_000,
  })
  return data
}

export async function getStoryJob(jobId: string): Promise<StoryJobStatus> {
  const { data } = await api.get<StoryJobStatus>(`/stories/jobs/${jobId}`)
  return data
}

export async function cancelStoryJob(jobId: string): Promise<StoryJobStatus> {
  const { data } = await api.post<StoryJobStatus>(`/stories/jobs/${jobId}/cancel`)
  return data
}

export function storyVideoUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}
