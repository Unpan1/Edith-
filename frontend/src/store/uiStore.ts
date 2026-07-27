import { create } from 'zustand'
import { DEFAULT_OPTIONS, type ProcessOptions, type Video } from '../types'

interface UiState {
  selectedVideoId: number | null
  uploadProgress: number
  isUploading: boolean
  playingClipId: number | null
  processOptions: ProcessOptions
  setSelectedVideoId: (id: number | null) => void
  setUploadProgress: (pct: number) => void
  setIsUploading: (v: boolean) => void
  setPlayingClipId: (id: number | null) => void
  selectedVideo: Video | null
  setSelectedVideo: (v: Video | null) => void
  setProcessOptions: (opts: ProcessOptions) => void
}

export const useUiStore = create<UiState>((set) => ({
  selectedVideoId: null,
  uploadProgress: 0,
  isUploading: false,
  playingClipId: null,
  selectedVideo: null,
  processOptions: DEFAULT_OPTIONS,
  setSelectedVideoId: (id) => set({ selectedVideoId: id }),
  setUploadProgress: (pct) => set({ uploadProgress: pct }),
  setIsUploading: (v) => set({ isUploading: v }),
  setPlayingClipId: (id) => set({ playingClipId: id }),
  setSelectedVideo: (v) => set({ selectedVideo: v, selectedVideoId: v?.id ?? null }),
  setProcessOptions: (opts) => set({ processOptions: opts }),
}))
