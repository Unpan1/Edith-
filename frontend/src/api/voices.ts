import { api } from './client'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export interface VoiceInfo {
  id: string
  name: string
  locale: string
  gender: string
  style: string
}

export interface SpeechMood {
  id: string
  label: string
  rate: string
  pitch: string
}

export interface VoiceListResponse {
  voices: VoiceInfo[]
  moods: SpeechMood[]
  note: string
}

export interface DialogueTurnPayload {
  voice_id: string
  text: string
  mood?: string
  character?: string
}

export interface VoiceJobStart {
  job_id: string
}

export interface VoiceJobStatus {
  job_id: string
  status: string
  progress: number
  detail: string
  eta_seconds?: number | null
  error?: string | null
  voice_id?: string | null
  filename?: string | null
  stream_url?: string | null
  download_url?: string | null
  mood?: string | null
  size_bytes?: number | null
  message?: string | null
}

export async function listVoices(): Promise<VoiceListResponse> {
  const { data } = await api.get<VoiceListResponse>('/voices')
  return data
}

export async function startSynthesizeVoice(payload: {
  text: string
  voice_id: string
  rate?: string
  pitch?: string
  mood?: string
  speed?: number
}): Promise<VoiceJobStart> {
  const { data } = await api.post<VoiceJobStart>('/voices/synthesize', payload, {
    timeout: 30_000,
  })
  return data
}

export async function startSynthesizeDialogue(payload: {
  turns: DialogueTurnPayload[]
  pause_ms?: number
  speed?: number
}): Promise<VoiceJobStart> {
  const { data } = await api.post<VoiceJobStart>('/voices/dialogue', payload, {
    timeout: 30_000,
  })
  return data
}

export interface VoicePreviewResult {
  voice_id: string
  filename: string
  size_bytes: number
  stream_url: string
  download_url: string
  mood: string
  message: string
  rate?: string | null
  speed?: number
}

export async function previewVoice(payload: {
  voice_id: string
  mood?: string
  speed?: number
  text?: string
}): Promise<VoicePreviewResult> {
  const { data } = await api.post<VoicePreviewResult>('/voices/preview', payload, {
    timeout: 60_000,
  })
  return data
}

export async function getVoiceJob(jobId: string): Promise<VoiceJobStatus> {
  const { data } = await api.get<VoiceJobStatus>(`/voices/jobs/${jobId}`)
  return data
}

export async function cancelVoiceJob(jobId: string): Promise<VoiceJobStatus> {
  const { data } = await api.post<VoiceJobStatus>(`/voices/jobs/${jobId}/cancel`)
  return data
}

export function voiceAudioUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}
