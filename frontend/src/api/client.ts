import axios from 'axios'
import type { Clip, ProcessOptions, ProcessResponse, Video } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 120_000,
})

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Video> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Video>('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
  return data
}

export async function importYoutubeVideo(url: string): Promise<{ job_id: string; message: string }> {
  const { data } = await api.post<{ job_id: string; message: string }>(
    '/upload/youtube',
    { url },
    { timeout: 30_000 },
  )
  return data
}

export interface YoutubeJobStatus {
  job_id: string
  kind: string
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  progress: number
  detail: string
  eta_seconds: number | null
  error: string | null
  video_id: number | null
  video?: Video | null
}

export async function getYoutubeJobStatus(jobId: string): Promise<YoutubeJobStatus> {
  const { data } = await api.get<YoutubeJobStatus>(`/upload/youtube/jobs/${jobId}`, {
    timeout: 15_000,
  })
  return data
}

export async function listVideos(): Promise<Video[]> {
  const { data } = await api.get<Video[]>('/videos')
  return data
}

export async function getVideo(id: number): Promise<Video> {
  const { data } = await api.get<Video>(`/videos/${id}`)
  return data
}

export async function processVideo(
  id: number,
  options: ProcessOptions,
): Promise<ProcessResponse> {
  const { data } = await api.post<ProcessResponse>(`/videos/${id}/process`, options)
  return data
}

export async function listClips(videoId: number): Promise<Clip[]> {
  const { data } = await api.get<Clip[]>(`/videos/${videoId}/clips`)
  return data
}

export async function getClip(id: number): Promise<Clip> {
  const { data } = await api.get<Clip>(`/clip/${id}`)
  return data
}

export async function deleteVideo(id: number): Promise<void> {
  await api.delete(`/video/${id}`)
}

export function clipStreamUrl(id: number): string {
  return `${API_URL}/clip/${id}/stream`
}

export function clipDownloadUrl(id: number): string {
  return `${API_URL}/clip/${id}/download`
}

export function clipThumbnailUrl(id: number): string {
  return `${API_URL}/clip/${id}/thumbnail`
}
