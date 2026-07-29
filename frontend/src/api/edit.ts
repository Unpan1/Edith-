import { api } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export interface EditAsset {
  id: string
  kind: string
  filename: string
  original_name: string
  size_bytes: number
  duration?: number | null
  width?: number | null
  height?: number | null
  stream_url: string
}

export type AudioMode = 'mix' | 'replace' | 'keep'

export interface EditRenderBody {
  video_ids: string[]
  audio_id?: string | null
  start?: number
  end?: number | null
  mirror?: boolean
  video_volume?: number
  audio_volume?: number
  audio_mode?: AudioMode
}

export interface EditJobStart {
  job_id: string
}

export interface EditJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds?: number | null
  error?: string | null
  filename?: string | null
  stream_url?: string | null
  download_url?: string | null
  duration?: number | null
  size_bytes?: number | null
}

export async function uploadEditAsset(
  file: File,
  kind: 'auto' | 'video' | 'audio' = 'auto',
  onProgress?: (pct: number) => void,
): Promise<EditAsset> {
  const form = new FormData()
  form.append('file', file)
  form.append('kind', kind)
  const { data } = await api.post<EditAsset>('/edit/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000,
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
  return data
}

export async function startEditRender(body: EditRenderBody): Promise<EditJobStart> {
  const { data } = await api.post<EditJobStart>('/edit/render', body, {
    timeout: 30_000,
  })
  return data
}

export async function getEditJob(jobId: string): Promise<EditJobStatus> {
  const { data } = await api.get<EditJobStatus>(`/edit/jobs/${jobId}`)
  return data
}

export async function cancelEditJob(jobId: string): Promise<EditJobStatus> {
  const { data } = await api.post<EditJobStatus>(`/edit/jobs/${jobId}/cancel`)
  return data
}

export function editFileUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}

export function formatBytes(n: number): string {
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${n} B`
}
