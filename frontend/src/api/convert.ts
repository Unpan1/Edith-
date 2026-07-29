import { api } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export type ConvertFormat = 'mp4' | 'mp3' | 'both'

export interface ConvertFile {
  kind: string
  filename: string
  size_bytes: number
  stream_url: string
  download_url: string
  display_name?: string | null
}

export interface ConvertJobStart {
  job_id: string
}

export interface ConvertJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds?: number | null
  error?: string | null
  title?: string | null
  duration?: number | null
  format?: string | null
  files: ConvertFile[]
}

export async function startYoutubeConvert(payload: {
  url: string
  format: ConvertFormat
}): Promise<ConvertJobStart> {
  const { data } = await api.post<ConvertJobStart>('/convert/youtube', payload, {
    timeout: 30_000,
  })
  return data
}

export async function getConvertJob(jobId: string): Promise<ConvertJobStatus> {
  const { data } = await api.get<ConvertJobStatus>(`/convert/youtube/jobs/${jobId}`)
  return data
}

export async function cancelConvertJob(jobId: string): Promise<ConvertJobStatus> {
  const { data } = await api.post<ConvertJobStatus>(
    `/convert/youtube/jobs/${jobId}/cancel`,
  )
  return data
}

export function convertFileUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}

export function formatBytes(n: number): string {
  if (n >= 1024 * 1024 * 1024) return `${(n / 1024 ** 3).toFixed(2)} GB`
  if (n >= 1024 * 1024) return `${(n / 1024 ** 2).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${n} B`
}
