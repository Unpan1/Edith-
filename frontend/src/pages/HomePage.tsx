import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  deleteVideo,
  getYoutubeJobStatus,
  importYoutubeVideo,
  listClips,
  listVideos,
  processVideo,
  uploadVideo,
} from '../api/client'
import { ClipCard } from '../components/ClipCard'
import { ClipPlayer } from '../components/ClipPlayer'
import { DropZone } from '../components/DropZone'
import { ProcessOptionsPanel } from '../components/ProcessOptionsPanel'
import {
  ProgressBar,
  buildProcessSteps,
  buildYoutubeSteps,
} from '../components/ProgressBar'
import { VideoCard } from '../components/VideoCard'
import { YoutubeImport } from '../components/YoutubeImport'
import { useUiStore } from '../store/uiStore'
import { ACTIVE_STATUSES, type Clip } from '../types'
import { formatDuration, formatSize } from '../utils/format'

export function HomePage() {
  const queryClient = useQueryClient()
  const {
    selectedVideoId,
    setSelectedVideoId,
    uploadProgress,
    isUploading,
    setIsUploading,
    setUploadProgress,
    playingClipId,
    setPlayingClipId,
    processOptions,
    setProcessOptions,
  } = useUiStore()

  const [youtubeJobId, setYoutubeJobId] = useState<string | null>(null)
  const [youtubeError, setYoutubeError] = useState<string | null>(null)

  const videosQuery = useQuery({
    queryKey: ['videos'],
    queryFn: listVideos,
    refetchInterval: (query) => {
      const list = query.state.data
      if (list?.some((v) => ACTIVE_STATUSES.includes(v.estado))) return 1500
      if (youtubeJobId) return 1500
      return false
    },
  })

  const youtubeJobQuery = useQuery({
    queryKey: ['youtube-job', youtubeJobId],
    queryFn: () => getYoutubeJobStatus(youtubeJobId!),
    enabled: youtubeJobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed') return false
      return 800
    },
  })

  useEffect(() => {
    const job = youtubeJobQuery.data
    if (!job || !youtubeJobId) return
    if (job.status === 'completed' && job.video_id) {
      setYoutubeJobId(null)
      setIsUploading(false)
      setUploadProgress(0)
      setYoutubeError(null)
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      setSelectedVideoId(job.video_id)
    } else if (job.status === 'failed') {
      setYoutubeJobId(null)
      setIsUploading(false)
      setUploadProgress(0)
      setYoutubeError(job.error || job.detail || 'Error al importar de YouTube')
    }
  }, [
    youtubeJobQuery.data,
    youtubeJobId,
    queryClient,
    setIsUploading,
    setUploadProgress,
    setSelectedVideoId,
  ])

  const selectedVideo = useMemo(
    () => videosQuery.data?.find((v) => v.id === selectedVideoId) ?? null,
    [videosQuery.data, selectedVideoId],
  )

  const clipsQuery = useQuery({
    queryKey: ['clips', selectedVideoId],
    queryFn: () => listClips(selectedVideoId!),
    enabled: selectedVideoId != null,
    refetchInterval:
      selectedVideo && ACTIVE_STATUSES.includes(selectedVideo.estado) ? 2000 : false,
  })

  useEffect(() => {
    if (selectedVideoId == null && videosQuery.data?.length) {
      setSelectedVideoId(videosQuery.data[0].id)
    }
  }, [videosQuery.data, selectedVideoId, setSelectedVideoId])

  useEffect(() => {
    if (selectedVideo?.opciones) {
      setProcessOptions({ ...processOptions, ...selectedVideo.opciones })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVideo?.id])

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadVideo(file, (pct) => setUploadProgress(pct)),
    onMutate: () => {
      setIsUploading(true)
      setUploadProgress(0)
      setYoutubeError(null)
    },
    onSuccess: (video) => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      setSelectedVideoId(video.id)
    },
    onSettled: () => {
      setIsUploading(false)
      setUploadProgress(0)
    },
  })

  const youtubeMutation = useMutation({
    mutationFn: (url: string) => importYoutubeVideo(url),
    onMutate: () => {
      setYoutubeError(null)
      setIsUploading(true)
      setUploadProgress(1)
    },
    onSuccess: (res) => {
      setYoutubeJobId(res.job_id)
    },
    onError: (err) => {
      setIsUploading(false)
      setUploadProgress(0)
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setYoutubeError(detail || (err as Error).message)
    },
  })

  const processMutation = useMutation({
    mutationFn: (id: number) => processVideo(id, processOptions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteVideo(id),
    onSuccess: (_d, id) => {
      if (selectedVideoId === id) setSelectedVideoId(null)
      queryClient.invalidateQueries({ queryKey: ['videos'] })
      queryClient.invalidateQueries({ queryKey: ['clips'] })
    },
  })

  const handleFile = useCallback(
    (file: File) => {
      uploadMutation.mutate(file)
    },
    [uploadMutation],
  )

  const handleYoutube = useCallback(
    (url: string) => {
      youtubeMutation.mutate(url)
    },
    [youtubeMutation],
  )

  const ytJob = youtubeJobQuery.data
  const ytActive =
    youtubeJobId != null && ytJob?.status !== 'completed' && ytJob?.status !== 'failed'
  const playingClip: Clip | undefined = clipsQuery.data?.find((c) => c.id === playingClipId)
  const optionsLocked =
    isUploading ||
    ytActive ||
    processMutation.isPending ||
    youtubeMutation.isPending ||
    (selectedVideo != null && ACTIVE_STATUSES.includes(selectedVideo.estado))

  const showImportProgress = isUploading || ytActive || youtubeMutation.isPending
  const importPct = ytJob?.progress ?? uploadProgress
  const importDetail = ytActive
    ? ytJob?.detail
    : youtubeMutation.isPending
      ? 'Iniciando descarga…'
      : uploadMutation.isPending
        ? `Subiendo archivo… ${uploadProgress}%`
        : null
  const importEta = ytJob?.eta_seconds ?? null

  return (
    <div className="mx-auto max-w-6xl space-y-10">
      <section className="space-y-4">
        <div>
          <h2 className="font-display text-2xl text-white sm:text-3xl">
            Genera clips virales en local
          </h2>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Sube un video o pega un link de YouTube. Elige monólogo o entrevista, formato
            vertical u horizontal, y genera clips o divide el video completo — todo en local.
          </p>
        </div>

        <DropZone onFile={handleFile} disabled={optionsLocked} />

        <div className="flex items-center gap-3 text-xs text-slate-600">
          <div className="h-px flex-1 bg-white/8" />
          <span>o</span>
          <div className="h-px flex-1 bg-white/8" />
        </div>

        <YoutubeImport
          onSubmit={handleYoutube}
          disabled={optionsLocked}
          loading={ytActive || youtubeMutation.isPending}
        />

        {showImportProgress && (
          <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
            <ProgressBar
              progress={importPct}
              label={
                ytActive || youtubeMutation.isPending
                  ? 'Importando YouTube'
                  : 'Subiendo archivo'
              }
              detail={importDetail}
              etaSeconds={importEta}
              steps={
                ytActive || youtubeMutation.isPending
                  ? buildYoutubeSteps(importPct, ytJob?.status || 'running')
                  : undefined
              }
            />
          </div>
        )}

        {uploadMutation.isError && (
          <p className="text-sm text-rose-400">
            Error al subir:{' '}
            {(uploadMutation.error as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail || uploadMutation.error.message}
          </p>
        )}

        {(youtubeError || youtubeMutation.isError) && (
          <p className="text-sm text-rose-400">
            Error al importar YouTube:{' '}
            {youtubeError ||
              (youtubeMutation.error as { response?: { data?: { detail?: string } } })?.response
                ?.data?.detail ||
              youtubeMutation.error?.message}
          </p>
        )}

        <ProcessOptionsPanel
          value={processOptions}
          onChange={setProcessOptions}
          disabled={optionsLocked}
        />

        {(uploadMutation.isSuccess || selectedVideo) && (
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-200">
            {selectedVideo && (
              <span>
                <strong className="text-white">{selectedVideo.nombre_original}</strong>
                {' · '}
                {formatDuration(selectedVideo.duracion)}
                {' · '}
                {formatSize(selectedVideo.tamano)}
              </span>
            )}
            <button
              type="button"
              disabled={optionsLocked || !selectedVideoId}
              onClick={() => selectedVideoId && processMutation.mutate(selectedVideoId)}
              className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-xs font-medium text-[#0a0c10] disabled:opacity-40"
            >
              Procesar con estas opciones
            </button>
          </div>
        )}
      </section>

      <div className="grid gap-8 lg:grid-cols-[340px_1fr]">
        <section className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Videos ({videosQuery.data?.length ?? 0})
          </h2>
          {videosQuery.isLoading && <p className="text-sm text-slate-500">Cargando…</p>}
          {videosQuery.isError && (
            <p className="text-sm text-rose-400">
              No se pudo conectar al backend. ¿Está corriendo en :8000?
            </p>
          )}
          <div className="space-y-3">
            {videosQuery.data?.map((video) => (
              <VideoCard
                key={video.id}
                video={video}
                selected={video.id === selectedVideoId}
                onSelect={() => setSelectedVideoId(video.id)}
                onProcess={() => processMutation.mutate(video.id)}
                onDelete={() => {
                  if (confirm(`¿Eliminar "${video.nombre_original}"?`)) {
                    deleteMutation.mutate(video.id)
                  }
                }}
                processing={processMutation.isPending}
              />
            ))}
            {!videosQuery.isLoading && !videosQuery.data?.length && (
              <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
                Aún no hay videos. Sube el primero.
              </p>
            )}
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex items-end justify-between gap-4">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Clips
              {selectedVideo ? ` · ${selectedVideo.nombre_original}` : ''}
            </h2>
            {clipsQuery.data && (
              <span className="text-xs text-slate-500">{clipsQuery.data.length} generados</span>
            )}
          </div>

          {selectedVideo && ACTIVE_STATUSES.includes(selectedVideo.estado) && (
            <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/5 p-4">
              <ProgressBar
                progress={selectedVideo.progreso}
                status={selectedVideo.estado}
                detail={selectedVideo.progreso_detalle}
                etaSeconds={selectedVideo.eta_segundos}
                steps={buildProcessSteps(selectedVideo.estado)}
              />
            </div>
          )}

          {!selectedVideoId && (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-16 text-center text-sm text-slate-500">
              Selecciona un video para ver sus clips
            </p>
          )}

          {selectedVideoId && clipsQuery.isLoading && (
            <p className="text-sm text-slate-500">Cargando clips…</p>
          )}

          {selectedVideoId && !clipsQuery.isLoading && !clipsQuery.data?.length && (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-16 text-center text-sm text-slate-500">
              {selectedVideo?.estado === 'completed'
                ? 'No se generaron clips'
                : selectedVideo?.estado === 'failed'
                  ? 'El procesamiento falló. Revisa el error e intenta de nuevo.'
                  : 'Configura las opciones y procesa el video'}
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            {clipsQuery.data?.map((clip) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                onPlay={() => setPlayingClipId(clip.id)}
              />
            ))}
          </div>
        </section>
      </div>

      {playingClip && (
        <ClipPlayer clip={playingClip} onClose={() => setPlayingClipId(null)} />
      )}
    </div>
  )
}
