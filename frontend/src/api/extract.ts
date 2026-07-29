import { api } from './client'

export interface TranscriptCue {
  start: number
  end: number
  text: string
  speaker?: number
}

export interface YoutubeTranscriptResult {
  title: string
  url: string
  language: string | null
  source: string
  text: string
  duration: number | null
  speakers_count: number
  cues: TranscriptCue[]
}

export interface ExtractJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds: number | null
  error: string | null
  result: YoutubeTranscriptResult | null
}

export async function startYoutubeExtract(payload: {
  url: string
  language?: string | null
  prefer_whisper?: boolean
  detect_speakers?: boolean
}): Promise<{ job_id: string }> {
  const { data } = await api.post<{ job_id: string }>('/extract/youtube', payload, {
    timeout: 30_000,
  })
  return data
}

export async function getExtractJob(jobId: string): Promise<ExtractJobStatus> {
  const { data } = await api.get<ExtractJobStatus>(`/extract/youtube/jobs/${jobId}`)
  return data
}
