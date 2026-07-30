import { useMutation, useQuery } from '@tanstack/react-query'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import {
  cancelEditJob,
  editFileUrl,
  extractErrorDetail,
  formatBytes,
  getEditJob,
  listEditAssets,
  startTimelineRender,
  uploadEditAsset,
  type EditAsset,
  type ExportFormat,
} from '../api/edit'
import { ProgressBar } from '../components/ProgressBar'
import {
  DEFAULT_TRACKS,
  FONT_OPTIONS,
  formatTime,
  projectDuration,
  uid,
  type TimelineClip,
  type TimelineTrack,
} from '../types/timeline'

const PX_PER_SEC = 48
const COLORS: Record<string, string> = {
  video: 'bg-sky-600/80 border-sky-400/50',
  image: 'bg-amber-600/80 border-amber-400/50',
  audio: 'bg-emerald-600/80 border-emerald-400/50',
  title: 'bg-rose-600/75 border-rose-400/50',
}

/** Estilos de publicación (proporción / resolución de salida) */
const PUBLISH_PRESETS = [
  {
    id: 'tiktok',
    label: 'TikTok / Reels / Shorts',
    width: 1080,
    height: 1920,
    hint: '9:16 vertical',
  },
  {
    id: 'youtube',
    label: 'YouTube (horizontal)',
    width: 1920,
    height: 1080,
    hint: '16:9',
  },
  {
    id: 'youtube_hd',
    label: 'YouTube 720p',
    width: 1280,
    height: 720,
    hint: '16:9',
  },
  {
    id: 'square',
    label: 'Instagram cuadrado',
    width: 1080,
    height: 1080,
    hint: '1:1',
  },
  {
    id: 'landscape_fb',
    label: 'Facebook / feed',
    width: 1280,
    height: 720,
    hint: '16:9',
  },
  {
    id: 'story',
    label: 'Stories',
    width: 1080,
    height: 1920,
    hint: '9:16',
  },
] as const

type PublishPresetId = (typeof PUBLISH_PRESETS)[number]['id']


const VIDEO_EXT = new Set(['.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'])
const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'])
const AUDIO_EXT = new Set(['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'])

function detectKind(file: File): 'video' | 'image' | 'audio' | null {
  const name = file.name.toLowerCase()
  const ext = name.includes('.') ? `.${name.split('.').pop()}` : ''
  if (file.type.startsWith('video/') || VIDEO_EXT.has(ext)) return 'video'
  if (file.type.startsWith('image/') || IMAGE_EXT.has(ext)) return 'image'
  if (file.type.startsWith('audio/') || AUDIO_EXT.has(ext)) return 'audio'
  return null
}

function activeAt(clips: TimelineClip[], t: number, kinds: TimelineClip['kind'][]) {
  return clips
    .filter(
      (c) =>
        kinds.includes(c.kind) && t >= c.start - 0.001 && t < c.start + c.duration,
    )
    .sort((a, b) => a.start - b.start)
}

export function BasicEditPage() {
  const [library, setLibrary] = useState<EditAsset[]>([])
  const [tracks] = useState<TimelineTrack[]>(DEFAULT_TRACKS)
  const [clips, setClips] = useState<TimelineClip[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [playhead, setPlayhead] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [libTab, setLibTab] = useState<'video' | 'image' | 'audio'>('video')
  const [mirror, setMirror] = useState(false)
  const [publishPreset, setPublishPreset] = useState<PublishPresetId>('tiktok')
  const [exportFormat, setExportFormat] = useState<ExportFormat>('mp4')
  const [dragOver, setDragOver] = useState(false)
  const [draggingLibrary, setDraggingLibrary] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [resultFormat, setResultFormat] = useState<ExportFormat>('mp4')
  const [resultMeta, setResultMeta] = useState<{
    duration?: number
    size?: number
  } | null>(null)

  const dragRef = useRef<{
    id: string
    mode: 'move' | 'resize'
    startX: number
    origStart: number
    origDur: number
  } | null>(null)
  const titleDragRef = useRef<{
    id: string
    startX: number
    startY: number
    origX: number
    origY: number
  } | null>(null)
  const playheadRef = useRef(0)
  const playingRef = useRef(false)
  const clipsRef = useRef(clips)
  const libraryRef = useRef(library)
  const durationRef = useRef(10)
  const rafRef = useRef(0)
  const lastTsRef = useRef(0)
  const lastUiUpdateRef = useRef(0)
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioMapRef = useRef<Map<string, HTMLAudioElement>>(new Map())
  const armedRef = useRef<Set<string>>(new Set()) // clips ya sincronizados en esta reproducción
  const previewBoxRef = useRef<HTMLDivElement>(null)
  const libraryDragAssetId = useRef<string | null>(null)

  const assetsQuery = useQuery({
    queryKey: ['edit-assets'],
    queryFn: listEditAssets,
    staleTime: 10_000,
  })

  useEffect(() => {
    if (assetsQuery.data) setLibrary(assetsQuery.data)
  }, [assetsQuery.data])

  // No sobrescribir playheadRef desde state mientras reproduce (evita el vaivén)
  useEffect(() => {
    if (!playingRef.current) playheadRef.current = playhead
  }, [playhead])
  useEffect(() => {
    playingRef.current = playing
  }, [playing])
  useEffect(() => {
    clipsRef.current = clips
  }, [clips])
  useEffect(() => {
    libraryRef.current = library
  }, [library])

  const duration = useMemo(() => projectDuration(clips), [clips])
  useEffect(() => {
    durationRef.current = duration
  }, [duration])

  const selected = clips.find((c) => c.id === selectedId) ?? null
  const timelineW = Math.max(800, duration * PX_PER_SEC + 80)

  const jobQuery = useQuery({
    queryKey: ['edit-job', jobId],
    queryFn: () => getEditJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      if (st === 'completed' || st === 'failed' || st === 'cancelled') return false
      return 1000
    },
  })

  useEffect(() => {
    const job = jobQuery.data
    if (!job || !jobId) return
    if (job.status === 'completed' && job.stream_url) {
      const t = Date.now()
      setResultUrl(editFileUrl(job.stream_url) + `?t=${t}`)
      setDownloadUrl(
        job.download_url
          ? editFileUrl(job.download_url)
          : editFileUrl(job.stream_url),
      )
      const ext = (job.filename || job.stream_url).split('.').pop()?.toLowerCase()
      if (
        ext === 'mp4' ||
        ext === 'webm' ||
        ext === 'mov' ||
        ext === 'mkv' ||
        ext === 'gif' ||
        ext === 'mp3' ||
        ext === 'wav'
      ) {
        setResultFormat(ext)
      }
      setResultMeta({
        duration: job.duration ?? undefined,
        size: job.size_bytes ?? undefined,
      })
      setJobId(null)
    } else if (job.status === 'failed') {
      setError(job.error || job.detail || 'Error al editar')
      setJobId(null)
    } else if (job.status === 'cancelled') {
      setJobId(null)
    }
  }, [jobQuery.data, jobId])

  const disposeAudio = useCallback((id?: string) => {
    if (id) {
      const el = audioMapRef.current.get(id)
      if (el) {
        el.pause()
        el.removeAttribute('src')
        el.load()
        audioMapRef.current.delete(id)
      }
      armedRef.current.delete(id)
      return
    }
    audioMapRef.current.forEach((a) => {
      a.pause()
      a.removeAttribute('src')
      a.load()
    })
    audioMapRef.current.clear()
    armedRef.current.clear()
  }, [])

  const ensureAudioEl = (clipId: string) => {
    let el = audioMapRef.current.get(clipId)
    if (!el) {
      el = new Audio()
      el.preload = 'auto'
      audioMapRef.current.set(clipId, el)
    }
    return el
  }

  /** Sincroniza medios: solo hace seek al activar un clip, no cada frame */
  const syncPreviewMedia = useCallback((t: number, shouldPlay: boolean) => {
    const list = clipsRef.current
    const lib = libraryRef.current
    const visual = activeAt(list, t, ['video', 'image']).at(-1)
    const videoEl = videoRef.current
    const nextArmed = new Set<string>()

    if (visual?.kind === 'video' && visual.assetId && videoEl) {
      const asset = lib.find((a) => a.id === visual.assetId)
      if (asset) {
        const url = editFileUrl(asset.stream_url)
        const localT = Math.max(0, visual.sourceOffset + (t - visual.start))
        const needsLoad = videoEl.dataset.clipId !== visual.id
        if (needsLoad) {
          videoEl.dataset.clipId = visual.id
          videoEl.dataset.assetId = asset.id
          videoEl.src = url
          try {
            videoEl.currentTime = localT
          } catch {
            /* ignore */
          }
        } else if (!shouldPlay) {
          // scrub estático
          if (Math.abs(videoEl.currentTime - localT) > 0.12) {
            try {
              videoEl.currentTime = localT
            } catch {
              /* ignore */
            }
          }
        } else if (Math.abs(videoEl.currentTime - localT) > 0.85) {
          // solo corregir desfase grande (evita el vaivén)
          try {
            videoEl.currentTime = localT
          } catch {
            /* ignore */
          }
        }
        // Preview: el video aporta imagen; su audio va por el mismo elemento (una sola vez)
        videoEl.muted = false
        videoEl.volume = Math.min(1, Math.max(0, visual.volume))
        nextArmed.add(visual.id)
        if (shouldPlay) {
          if (videoEl.paused) void videoEl.play().catch(() => undefined)
        } else {
          videoEl.pause()
        }
      }
    } else if (videoEl) {
      videoEl.pause()
      videoEl.dataset.clipId = ''
    }

    const audioClips = activeAt(list, t, ['audio'])
    const activeIds = new Set(audioClips.map((c) => c.id))

    // Pausar y desarmar audios que ya no están activos
    audioMapRef.current.forEach((el, id) => {
      if (!activeIds.has(id)) {
        el.pause()
        armedRef.current.delete(id)
      }
    })

    for (const clip of audioClips) {
      if (!clip.assetId) continue
      const asset = lib.find((a) => a.id === clip.assetId)
      if (!asset) continue
      const el = ensureAudioEl(clip.id)
      const url = editFileUrl(asset.stream_url)
      const localT = Math.max(0, clip.sourceOffset + (t - clip.start))
      const justArmed = !armedRef.current.has(clip.id)

      if (el.dataset.assetId !== asset.id) {
        el.dataset.assetId = asset.id
        el.src = url
      }
      el.volume = Math.min(1, Math.max(0, clip.volume))

      if (justArmed || !shouldPlay) {
        if (Math.abs(el.currentTime - localT) > 0.08) {
          try {
            el.currentTime = localT
          } catch {
            /* ignore */
          }
        }
      } else if (Math.abs(el.currentTime - localT) > 0.85) {
        try {
          el.currentTime = localT
        } catch {
          /* ignore */
        }
      }

      nextArmed.add(clip.id)
      if (shouldPlay) {
        if (el.paused) void el.play().catch(() => undefined)
      } else {
        el.pause()
      }
    }

    // Actualizar armed solo con los activos ahora
    armedRef.current = nextArmed
  }, [])

  const stopPlayback = useCallback(() => {
    setPlaying(false)
    playingRef.current = false
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = 0
    lastTsRef.current = 0
    videoRef.current?.pause()
    audioMapRef.current.forEach((a) => a.pause())
    armedRef.current.clear()
  }, [])

  const tick = useCallback(
    (ts: number) => {
      if (!playingRef.current) return
      if (!lastTsRef.current) lastTsRef.current = ts
      const dt = Math.min(0.1, (ts - lastTsRef.current) / 1000)
      lastTsRef.current = ts
      let next = playheadRef.current + dt
      const max = durationRef.current
      if (next >= max) {
        next = max
        playheadRef.current = next
        setPlayhead(next)
        syncPreviewMedia(next, false)
        stopPlayback()
        return
      }
      playheadRef.current = next
      // UI a ~12 fps para no pelear con el clock de audio/video
      if (ts - lastUiUpdateRef.current > 80) {
        lastUiUpdateRef.current = ts
        setPlayhead(next)
      }
      syncPreviewMedia(next, true)
      rafRef.current = requestAnimationFrame(tick)
    },
    [stopPlayback, syncPreviewMedia],
  )

  const togglePlay = () => {
    if (playing) {
      stopPlayback()
      setPlayhead(playheadRef.current)
      return
    }
    if (clips.length === 0) {
      setError('Añade clips a la timeline para previsualizar')
      return
    }
    setError(null)
    if (playheadRef.current >= durationRef.current - 0.05) {
      playheadRef.current = 0
      setPlayhead(0)
    }
    armedRef.current.clear()
    setPlaying(true)
    playingRef.current = true
    lastTsRef.current = 0
    lastUiUpdateRef.current = 0
    syncPreviewMedia(playheadRef.current, true)
    rafRef.current = requestAnimationFrame(tick)
  }

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      disposeAudio()
    }
  }, [disposeAudio])

  // Scrub estático (solo si no está reproduciendo)
  useEffect(() => {
    if (!playing) {
      armedRef.current.clear()
      syncPreviewMedia(playhead, false)
    }
  }, [playhead, playing, clips, library, syncPreviewMedia])

  const uploadMutation = useMutation({
    mutationFn: async (items: { file: File; kind: 'video' | 'image' | 'audio' }[]) => {
      if (!items.length) throw new Error('No se seleccionó ningún archivo')
      const uploaded: EditAsset[] = []
      for (const { file, kind } of items) {
        setUploadPct(0)
        uploaded.push(await uploadEditAsset(file, kind, setUploadPct))
      }
      return uploaded
    },
    onSuccess: (uploaded) => {
      setLibrary((prev) => {
        const ids = new Set(uploaded.map((a) => a.id))
        return [...uploaded, ...prev.filter((a) => !ids.has(a.id))]
      })
      setUploadPct(null)
      setError(null)
      const kinds = new Set(uploaded.map((a) => a.kind))
      if (kinds.size === 1) setLibTab([...kinds][0] as 'video' | 'image' | 'audio')
      setInfo(
        `${uploaded.length} archivo(s) listos. Clic o arrástralos a la timeline (puedes repetirlos).`,
      )
      void assetsQuery.refetch()
    },
    onError: (err) => {
      setUploadPct(null)
      setError(extractErrorDetail(err))
      setInfo(null)
    },
  })

  const importFiles = (files: FileList | File[] | null) => {
    if (!files?.length) return
    const items: { file: File; kind: 'video' | 'image' | 'audio' }[] = []
    const skipped: string[] = []
    for (const f of Array.from(files)) {
      const kind = detectKind(f)
      if (!kind) {
        skipped.push(f.name)
        continue
      }
      items.push({ file: f, kind })
    }
    if (skipped.length) {
      setError(`No soportados: ${skipped.slice(0, 3).join(', ')}`)
    }
    if (!items.length) return
    setInfo('Subiendo…')
    uploadMutation.mutate(items)
  }

  const selectedPreset =
    PUBLISH_PRESETS.find((p) => p.id === publishPreset) ?? PUBLISH_PRESETS[0]
  const previewAspect =
    selectedPreset.width / selectedPreset.height

  const renderMutation = useMutation({
    mutationFn: () =>
      startTimelineRender({
        clips: clips.map((c) => ({
          id: c.id,
          kind: c.kind,
          asset_id: c.assetId ?? null,
          track: c.trackId,
          start: Number(c.start.toFixed(3)),
          duration: Number(c.duration.toFixed(3)),
          source_offset: Number((c.sourceOffset || 0).toFixed(3)),
          volume: c.volume,
          text: c.text ?? null,
          font_family: c.fontFamily ?? 'Arial',
          font_size: c.fontSize ?? 48,
          color: c.color ?? 'white',
          x_percent: c.xPercent ?? 50,
          y_percent: c.yPercent ?? 18,
        })),
        width: selectedPreset.width,
        height: selectedPreset.height,
        mirror,
        export_format: exportFormat,
      }),
    onMutate: () => {
      stopPlayback()
      setError(null)
      setResultUrl(null)
      setDownloadUrl(null)
      setResultMeta(null)
    },
    onSuccess: (res) => setJobId(res.job_id),
    onError: (err) => setError(extractErrorDetail(err)),
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelEditJob(jobId!),
    onSuccess: () => setJobId(null),
  })

  const busy =
    jobId != null || renderMutation.isPending || uploadMutation.isPending
  const canRender =
    clips.length > 0 &&
    (exportFormat === 'mp3' ||
      exportFormat === 'wav' ||
      clips.some(
        (c) => c.kind === 'video' || c.kind === 'image' || c.kind === 'title',
      )) &&
    !busy
  const progress = jobQuery.data?.progress ?? (renderMutation.isPending ? 1 : 0)
  const detail =
    jobQuery.data?.detail ?? (renderMutation.isPending ? 'Enviando…' : '')

  const nextStartOnTrack = useCallback(
    (trackId: string, fromTime?: number) => {
      const base = fromTime ?? playheadRef.current
      const onTrack = clipsRef.current.filter((c) => c.trackId === trackId)
      if (!onTrack.length) return Math.max(0, base)
      return Math.max(base, ...onTrack.map((c) => c.start + c.duration))
    },
    [],
  )

  const placeAssetOnTimeline = useCallback(
    (asset: EditAsset, opts?: { trackId?: string; start?: number }) => {
      setError(null)
      setInfo(null)
      stopPlayback()

      const rawKind = String(asset.kind || '').toLowerCase().trim()
      const name = (asset.original_name || '').toLowerCase()
      const ext = name.includes('.') ? `.${name.split('.').pop()}` : ''
      let kind: 'video' | 'image' | 'audio' | null =
        rawKind === 'video' || rawKind === 'image' || rawKind === 'audio'
          ? rawKind
          : null
      if (!kind) {
        if (IMAGE_EXT.has(ext)) kind = 'image'
        else if (VIDEO_EXT.has(ext)) kind = 'video'
        else if (AUDIO_EXT.has(ext)) kind = 'audio'
      }
      if (!kind) {
        setError(`No se pudo añadir “${asset.original_name}” (tipo desconocido)`)
        return
      }

      if (kind === 'audio') {
        const trackId =
          opts?.trackId === 'A1' || opts?.trackId === 'A2'
            ? opts.trackId
            : clipsRef.current.filter((c) => c.trackId === 'A1').length <=
                clipsRef.current.filter((c) => c.trackId === 'A2').length
              ? 'A1'
              : 'A2'
        const start =
          opts?.start != null
            ? Math.max(0, opts.start)
            : nextStartOnTrack(trackId)
        const clip: TimelineClip = {
          id: uid('a'),
          kind: 'audio',
          assetId: asset.id,
          trackId,
          start: Number(start.toFixed(2)),
          duration: Math.max(1, asset.duration || 10),
          sourceOffset: 0,
          volume: 1,
          label: asset.original_name,
        }
        setClips((p) => [...p, clip])
        setSelectedId(clip.id)
        setInfo(`Audio añadido en ${trackId}.`)
        return
      }

      // video o image → siempre pista V1
      const isImage = kind === 'image'
      const start =
        opts?.start != null ? Math.max(0, opts.start) : nextStartOnTrack('V1')
      const clip: TimelineClip = {
        id: uid(isImage ? 'img' : 'v'),
        kind: isImage ? 'image' : 'video',
        assetId: asset.id,
        trackId: 'V1',
        start: Number(start.toFixed(2)),
        duration: isImage ? 5 : Math.max(0.5, asset.duration || 5),
        sourceOffset: 0,
        volume: isImage ? 0 : 1,
        label: asset.original_name,
      }
      setClips((p) => [...p, clip])
      setSelectedId(clip.id)
      setInfo(
        `${isImage ? 'Foto' : 'Video'} añadido a Video 1 (${clip.duration}s). Arrástralo o alarga el borde derecho.`,
      )
    },
    [nextStartOnTrack, stopPlayback],
  )

  const addAssetToTimeline = (asset: EditAsset) => {
    placeAssetOnTimeline(asset)
  }

  const addTitle = () => {
    stopPlayback()
    const clip: TimelineClip = {
      id: uid('t'),
      kind: 'title',
      trackId: 'T1',
      start: playheadRef.current,
      duration: 4,
      sourceOffset: 0,
      volume: 0,
      label: 'Título',
      text: 'Mi título',
      fontFamily: 'Arial',
      fontSize: 56,
      color: 'white',
      xPercent: 50,
      yPercent: 20,
    }
    setClips((p) => [...p, clip])
    setSelectedId(clip.id)
    setInfo('Título en pista Títulos. Arrástralo en la vista previa y en la timeline.')
  }

  const updateClip = (id: string, patch: Partial<TimelineClip>) => {
    setClips((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)))
  }

  const removeClip = (id: string) => {
    stopPlayback()
    disposeAudio(id)
    setClips((prev) => prev.filter((c) => c.id !== id))
    if (selectedId === id) setSelectedId(null)
    setInfo('Clip eliminado de la timeline. El archivo sigue en la biblioteca.')
  }

  const splitAtPlayhead = () => {
    const t = playhead
    const target =
      (selected &&
      t > selected.start + 0.15 &&
      t < selected.start + selected.duration - 0.15
        ? selected
        : null) ||
      clips.find(
        (c) => t > c.start + 0.15 && t < c.start + c.duration - 0.15,
      )
    if (!target) {
      setError('Coloca el playhead dentro de un clip (no en los bordes) para cortar')
      return
    }
    const leftDur = t - target.start
    const rightDur = target.start + target.duration - t
    const right: TimelineClip = {
      ...target,
      id: uid('cut'),
      start: t,
      duration: Number(rightDur.toFixed(3)),
      sourceOffset: Number((target.sourceOffset + leftDur).toFixed(3)),
      label: `${target.label} (2)`,
    }
    setClips((prev) =>
      prev.flatMap((c) =>
        c.id === target.id
          ? [
              {
                ...c,
                duration: Number(leftDur.toFixed(3)),
                label: c.label.replace(/ \(2\)$/, '') + '',
              },
              right,
            ]
          : [c],
      ),
    )
    setSelectedId(right.id)
    setError(null)
    setInfo('Clip cortado en dos. Puedes eliminar o duplicar cada parte.')
  }

  const duplicateSelected = () => {
    if (!selected) {
      setError('Selecciona un clip para duplicar')
      return
    }
    const copy: TimelineClip = {
      ...selected,
      id: uid('dup'),
      start: selected.start + selected.duration,
      label: `${selected.label} copia`,
    }
    setClips((p) => [...p, copy])
    setSelectedId(copy.id)
    setError(null)
  }

  const onClipPointerDown = (
    e: ReactPointerEvent,
    clip: TimelineClip,
    mode: 'move' | 'resize',
  ) => {
    e.stopPropagation()
    e.preventDefault()
    stopPlayback()
    setSelectedId(clip.id)
    dragRef.current = {
      id: clip.id,
      mode,
      startX: e.clientX,
      origStart: clip.start,
      origDur: clip.duration,
    }
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  const onTitlePointerDown = (e: ReactPointerEvent, clip: TimelineClip) => {
    e.stopPropagation()
    e.preventDefault()
    stopPlayback()
    setSelectedId(clip.id)
    titleDragRef.current = {
      id: clip.id,
      startX: e.clientX,
      startY: e.clientY,
      origX: clip.xPercent ?? 50,
      origY: clip.yPercent ?? 20,
    }
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      const d = dragRef.current
      if (d) {
        const dx = (e.clientX - d.startX) / PX_PER_SEC
        if (d.mode === 'move') {
          updateClip(d.id, { start: Math.max(0, Number((d.origStart + dx).toFixed(2))) })
        } else {
          updateClip(d.id, {
            duration: Math.max(0.5, Number((d.origDur + dx).toFixed(2))),
          })
        }
        return
      }
      const td = titleDragRef.current
      const box = previewBoxRef.current
      if (td && box) {
        const rect = box.getBoundingClientRect()
        const dxPct = ((e.clientX - td.startX) / rect.width) * 100
        const dyPct = ((e.clientY - td.startY) / rect.height) * 100
        updateClip(td.id, {
          xPercent: Math.min(95, Math.max(5, Number((td.origX + dxPct).toFixed(1)))),
          yPercent: Math.min(95, Math.max(5, Number((td.origY + dyPct).toFixed(1)))),
        })
      }
    }
    const onUp = () => {
      dragRef.current = null
      titleDragRef.current = null
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
    }
  }, [])

  const onDropFiles = (e: DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    setDraggingLibrary(false)
    const assetId =
      e.dataTransfer.getData('application/x-clipai-asset') ||
      e.dataTransfer.getData('text/plain') ||
      libraryDragAssetId.current
    if (assetId && libraryRef.current.some((a) => a.id === assetId)) {
      libraryDragAssetId.current = null
      const asset = libraryRef.current.find((a) => a.id === assetId)
      if (asset) placeAssetOnTimeline(asset)
      return
    }
    libraryDragAssetId.current = null
    if (e.dataTransfer.files?.length) importFiles(e.dataTransfer.files)
  }

  const dropAssetOnTrack = (
    e: DragEvent,
    track: TimelineTrack,
    trackBodyEl: HTMLElement,
  ) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    setDraggingLibrary(false)
    const assetId =
      e.dataTransfer.getData('application/x-clipai-asset') ||
      e.dataTransfer.getData('text/plain') ||
      libraryDragAssetId.current
    libraryDragAssetId.current = null

    if (assetId) {
      const asset = libraryRef.current.find((a) => a.id === assetId)
      if (!asset) {
        setError('No se encontró el archivo en la biblioteca')
        return
      }
      const rect = trackBodyEl.getBoundingClientRect()
      const x = e.clientX - rect.left
      const start = Math.max(0, x / PX_PER_SEC)
      // Fotos/videos siempre a V1; audios a A1/A2 (o la pista de audio bajo el cursor)
      if (asset.kind === 'audio') {
        const audioTrack =
          track.kind === 'audio' ? track.id : ('A1' as const)
        placeAssetOnTimeline(asset, { trackId: audioTrack, start })
      } else {
        placeAssetOnTimeline(asset, { start })
      }
      return
    }

    if (e.dataTransfer.files?.length) importFiles(e.dataTransfer.files)
  }

  const libAssets = library.filter((a) => a.kind === libTab)
  const libCounts = useMemo(
    () => ({
      video: library.filter((a) => a.kind === 'video').length,
      image: library.filter((a) => a.kind === 'image').length,
      audio: library.filter((a) => a.kind === 'audio').length,
    }),
    [library],
  )

  const visualAtPlayhead = useMemo(
    () => activeAt(clips, playhead, ['video', 'image']).at(-1) ?? null,
    [clips, playhead],
  )
  const previewAsset = useMemo(() => {
    if (!visualAtPlayhead?.assetId) return null
    return library.find((a) => a.id === visualAtPlayhead.assetId) ?? null
  }, [visualAtPlayhead, library])

  const titlesAtPlayhead = useMemo(
    () => activeAt(clips, playhead, ['title']),
    [clips, playhead],
  )

  const rulerMarks = useMemo(() => {
    const marks: number[] = []
    for (let t = 0; t <= duration + 0.01; t += 1) marks.push(t)
    return marks
  }, [duration])

  const seekTo = (t: number) => {
    stopPlayback()
    const v = Math.max(0, Math.min(durationRef.current, t))
    playheadRef.current = v
    setPlayhead(v)
    armedRef.current.clear()
  }

  return (
    <div
      className="-mx-2 space-y-3 sm:-mx-0"
      onDragOver={(e) => {
        e.preventDefault()
        // Solo overlay de importación si vienen archivos del sistema, no de la biblioteca
        if (!draggingLibrary && e.dataTransfer.types.includes('Files')) {
          setDragOver(true)
        }
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDropFiles}
    >
      {dragOver && !draggingLibrary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-cyan-950/70 backdrop-blur-sm">
          <p className="rounded-2xl border border-cyan-400/40 bg-[#0e1118] px-8 py-6 text-lg text-cyan-100">
            Suelta videos, fotos o audios para importar
          </p>
        </div>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-cyan-400/90">
            Editor · Timeline
          </p>
          <h1 className="font-display mt-1 text-2xl text-white sm:text-3xl">
            Editor de video
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Arrastra archivos, previsualiza con play, corta clips y mueve títulos con el
            ratón.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex flex-col gap-1 rounded-lg border border-cyan-400/30 bg-cyan-500/5 px-3 py-2 text-xs text-slate-300">
            <span className="text-[10px] uppercase tracking-wide text-cyan-300/90">
              Estilo / plataforma
            </span>
            <select
              value={publishPreset}
              disabled={busy}
              onChange={(e) =>
                setPublishPreset(e.target.value as PublishPresetId)
              }
              className="rounded-md border border-white/10 bg-[#12151e] px-2 py-1 text-xs text-white"
            >
              {PUBLISH_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label} · {p.hint} ({p.width}×{p.height})
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300">
            <span className="text-[10px] uppercase tracking-wide text-slate-500">
              Archivo
            </span>
            <select
              value={exportFormat}
              disabled={busy}
              onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
              className="rounded-md border border-white/10 bg-[#12151e] px-2 py-1 text-xs text-white"
            >
              <option value="mp4">MP4</option>
              <option value="webm">WebM</option>
              <option value="mov">MOV</option>
              <option value="mkv">MKV</option>
              <option value="gif">GIF</option>
              <option value="mp3">MP3 (audio)</option>
              <option value="wav">WAV (audio)</option>
            </select>
          </label>
          <label className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={mirror}
              disabled={busy}
              onChange={(e) => setMirror(e.target.checked)}
              className="accent-cyan-400"
            />
            Espejo
          </label>
          <button
            type="button"
            disabled={!canRender}
            onClick={() => renderMutation.mutate()}
            className="rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 px-5 py-2.5 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
          >
            {busy && jobId
              ? 'Exportando…'
              : `Exportar ${selectedPreset.hint}`}
          </button>
          {jobId && (
            <button
              type="button"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              className="rounded-xl border border-rose-400/40 px-4 py-2.5 text-sm text-rose-200"
            >
              Cancelar
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[260px_1fr]">
        <aside className="flex max-h-[460px] flex-col overflow-hidden rounded-xl border border-dashed border-white/15 bg-[#0e1118]">
          <div className="flex border-b border-white/8">
            {(
              [
                ['video', 'Videos'],
                ['image', 'Fotos'],
                ['audio', 'Audios'],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setLibTab(id)}
                className={[
                  'flex-1 px-2 py-2.5 text-xs font-medium',
                  libTab === id
                    ? 'border-b-2 border-cyan-400 text-cyan-200'
                    : 'text-slate-500 hover:text-slate-300',
                ].join(' ')}
              >
                {label}
                {libCounts[id] > 0 ? ` (${libCounts[id]})` : ''}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between gap-2 border-b border-white/8 px-3 py-2">
            <span className="text-[11px] text-slate-500">
              Arrastra aquí · {libAssets.length} archivo(s)
            </span>
            <label className="cursor-pointer rounded-md border border-cyan-400/35 bg-cyan-400/10 px-2.5 py-1 text-[11px] text-cyan-100 hover:bg-cyan-400/20">
              + Importar
              <input
                type="file"
                multiple
                disabled={busy}
                className="hidden"
                accept="video/*,image/*,audio/*,.mp4,.mov,.mkv,.webm,.jpg,.jpeg,.png,.webp,.mp3,.wav,.m4a,.aac"
                onChange={(e) => {
                  importFiles(e.target.files)
                  e.target.value = ''
                }}
              />
            </label>
          </div>
          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {libAssets.length === 0 && (
              <p className="px-2 py-6 text-center text-xs text-slate-600">
                Arrastra o importa {libTab === 'video' ? 'videos' : libTab === 'image' ? 'fotos' : 'audios'}
              </p>
            )}
            {libAssets.map((a) => (
              <div
                key={a.id}
                className="flex w-full items-center gap-1 rounded-lg border border-transparent px-1 py-1 hover:border-white/10 hover:bg-white/5"
              >
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => addAssetToTimeline(a)}
                  className="flex min-w-0 flex-1 items-center gap-2 px-1 py-1.5 text-left"
                  title="Clic para añadir a Video 1 / Audio"
                >
                  {a.kind === 'image' ? (
                    <img
                      src={editFileUrl(a.stream_url)}
                      alt=""
                      className="h-10 w-10 shrink-0 rounded object-cover bg-black"
                    />
                  ) : (
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-white/5 text-[10px] uppercase text-slate-500">
                      {a.kind === 'audio' ? '♪' : '▶'}
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs text-white">{a.original_name}</p>
                    <p className="text-[10px] text-slate-500">
                      {a.duration != null
                        ? `${a.duration.toFixed(1)}s`
                        : a.kind === 'image'
                          ? 'foto · 5s al añadir'
                          : '—'}
                      {` · ${formatBytes(a.size_bytes)}`}
                    </p>
                  </div>
                </button>
                <button
                  type="button"
                  draggable
                  disabled={busy}
                  onDragStart={(e) => {
                    libraryDragAssetId.current = a.id
                    setDraggingLibrary(true)
                    e.dataTransfer.setData('application/x-clipai-asset', a.id)
                    e.dataTransfer.setData('text/plain', a.id)
                    e.dataTransfer.effectAllowed = 'copy'
                  }}
                  onDragEnd={() => {
                    libraryDragAssetId.current = null
                    setDraggingLibrary(false)
                  }}
                  className="shrink-0 cursor-grab rounded border border-white/10 px-2 py-3 text-[10px] text-slate-400 active:cursor-grabbing"
                  title="Arrastra a la timeline"
                >
                  ⋮⋮
                </button>
              </div>
            ))}
          </div>
          <div className="border-t border-white/8 p-2">
            <button
              type="button"
              disabled={busy}
              onClick={addTitle}
              className="w-full rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-100 hover:bg-rose-500/20"
            >
              + Añadir título (a la timeline)
            </button>
          </div>
        </aside>

        <div className="grid gap-3 xl:grid-cols-[1fr_260px]">
          <section className="overflow-hidden rounded-xl border border-white/10 bg-[#0e1118]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/8 px-3 py-2">
              <span className="text-xs text-slate-400">
                Vista previa · {selectedPreset.label} ({selectedPreset.width}×
                {selectedPreset.height})
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => seekTo(0)}
                  className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/5"
                  title="Ir al inicio"
                >
                  ⏮
                </button>
                <button
                  type="button"
                  onClick={togglePlay}
                  className="rounded-lg bg-cyan-500/20 px-4 py-1.5 text-xs font-medium text-cyan-100 hover:bg-cyan-500/30"
                >
                  {playing ? '⏸ Pausar' : '▶ Reproducir'}
                </button>
                <button
                  type="button"
                  onClick={stopPlayback}
                  className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/5"
                >
                  ⏹
                </button>
                <span className="font-mono text-[11px] text-slate-500">
                  {formatTime(playhead)} / {formatTime(duration)}
                </span>
              </div>
            </div>
            <div className="flex justify-center bg-[#080a0e] p-3">
              <div
                ref={previewBoxRef}
                className="relative flex max-h-[420px] w-full max-w-[360px] items-center justify-center overflow-hidden bg-black shadow-lg shadow-black/40"
                style={{
                  aspectRatio: `${selectedPreset.width} / ${selectedPreset.height}`,
                  maxWidth: previewAspect < 1 ? 280 : 560,
                }}
              >
              {/* Video siempre montado para sync de audio/video */}
              <video
                ref={videoRef}
                className={[
                  'max-h-full max-w-full',
                  previewAsset?.kind === 'video' ? 'block' : 'hidden',
                  mirror ? 'scale-x-[-1]' : '',
                ].join(' ')}
                playsInline
              />
              {previewAsset?.kind === 'image' && (
                <img
                  src={editFileUrl(previewAsset.stream_url)}
                  alt=""
                  className={[
                    'max-h-full max-w-full object-contain',
                    mirror ? 'scale-x-[-1]' : '',
                  ].join(' ')}
                />
              )}
              {!previewAsset && !titlesAtPlayhead.length && (
                <p className="text-sm text-slate-600">
                  Importa medios y colócalos en la timeline
                </p>
              )}
              {titlesAtPlayhead.map((title) => (
                <div
                  key={title.id}
                  onPointerDown={(e) => onTitlePointerDown(e, title)}
                  className={[
                    'absolute z-10 max-w-[90%] -translate-x-1/2 -translate-y-1/2 cursor-move select-none px-2 py-1',
                    selectedId === title.id
                      ? 'rounded ring-2 ring-cyan-300/80'
                      : '',
                  ].join(' ')}
                  style={{
                    left: `${title.xPercent ?? 50}%`,
                    top: `${title.yPercent ?? 20}%`,
                    fontFamily: title.fontFamily || 'Arial',
                    fontSize: Math.max(14, (title.fontSize || 48) * 0.42),
                    color: title.color || 'white',
                    textShadow: '0 2px 8px rgba(0,0,0,.85)',
                    textAlign: 'center',
                  }}
                  title="Arrastra para mover el título"
                >
                  {title.text || 'Título'}
                </div>
              ))}
            </div>
            </div>
          </section>

          <section className="rounded-xl border border-white/10 bg-[#0e1118] p-3">
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">
              Propiedades
            </h2>
            {!selected ? (
              <p className="text-xs text-slate-600">
                Selecciona un clip en la timeline para editarlo.
              </p>
            ) : (
              <div className="space-y-3">
                <p className="truncate text-sm text-white">{selected.label}</p>
                <p className="text-[10px] uppercase text-slate-500">{selected.kind}</p>
                <label className="block space-y-1">
                  <span className="text-[11px] text-slate-500">Inicio (s)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={selected.start}
                    disabled={busy}
                    onChange={(e) =>
                      updateClip(selected.id, {
                        start: Math.max(0, Number(e.target.value) || 0),
                      })
                    }
                    className="w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[11px] text-slate-500">Duración (s)</span>
                  <input
                    type="number"
                    min={0.5}
                    step={0.1}
                    value={selected.duration}
                    disabled={busy}
                    onChange={(e) =>
                      updateClip(selected.id, {
                        duration: Math.max(0.5, Number(e.target.value) || 0.5),
                      })
                    }
                    className="w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                  />
                </label>

                {(selected.kind === 'audio' || selected.kind === 'video') && (
                  <label className="block space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>Volumen</span>
                      <span className="font-mono text-slate-300">
                        {Math.round(selected.volume * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={200}
                      step={5}
                      value={Math.round(selected.volume * 100)}
                      disabled={busy}
                      onChange={(e) =>
                        updateClip(selected.id, {
                          volume: Number(e.target.value) / 100,
                        })
                      }
                      className="w-full accent-emerald-400"
                    />
                  </label>
                )}

                {selected.kind === 'title' && (
                  <>
                    <label className="block space-y-1">
                      <span className="text-[11px] text-slate-500">Texto</span>
                      <input
                        type="text"
                        value={selected.text || ''}
                        disabled={busy}
                        onChange={(e) =>
                          updateClip(selected.id, {
                            text: e.target.value,
                            label: e.target.value || 'Título',
                          })
                        }
                        className="w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                      />
                    </label>
                    <label className="block space-y-1">
                      <span className="text-[11px] text-slate-500">Fuente</span>
                      <select
                        value={selected.fontFamily || 'Arial'}
                        disabled={busy}
                        onChange={(e) =>
                          updateClip(selected.id, { fontFamily: e.target.value })
                        }
                        className="w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                      >
                        {FONT_OPTIONS.map((f) => (
                          <option key={f} value={f}>
                            {f}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block space-y-1">
                      <div className="flex justify-between text-[11px] text-slate-500">
                        <span>Tamaño</span>
                        <span className="font-mono">{selected.fontSize || 48}px</span>
                      </div>
                      <input
                        type="range"
                        min={12}
                        max={160}
                        value={selected.fontSize || 48}
                        disabled={busy}
                        onChange={(e) =>
                          updateClip(selected.id, {
                            fontSize: Number(e.target.value),
                          })
                        }
                        className="w-full accent-rose-400"
                      />
                      <input
                        type="number"
                        min={12}
                        max={200}
                        value={selected.fontSize || 48}
                        disabled={busy}
                        onChange={(e) =>
                          updateClip(selected.id, {
                            fontSize: Math.min(
                              200,
                              Math.max(12, Number(e.target.value) || 48),
                            ),
                          })
                        }
                        className="mt-1 w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                      />
                    </label>
                    <p className="text-[10px] text-slate-500">
                      Arrastra el título en la vista previa para moverlo. En la pista
                      Títulos ajustas cuándo aparece.
                    </p>
                  </>
                )}

                {selected.kind === 'audio' && (
                  <label className="block space-y-1">
                    <span className="text-[11px] text-slate-500">Pista</span>
                    <select
                      value={selected.trackId}
                      disabled={busy}
                      onChange={(e) =>
                        updateClip(selected.id, { trackId: e.target.value })
                      }
                      className="w-full rounded-lg border border-white/10 bg-[#12151e] px-2 py-1.5 text-sm text-white"
                    >
                      <option value="A1">Audio 1</option>
                      <option value="A2">Audio 2</option>
                    </select>
                  </label>
                )}

                <div className="grid grid-cols-3 gap-1.5 pt-1">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={splitAtPlayhead}
                    className="rounded-lg border border-amber-400/30 px-1 py-2 text-[10px] text-amber-100 hover:bg-amber-500/10"
                  >
                    Cortar
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={duplicateSelected}
                    className="rounded-lg border border-sky-400/30 px-1 py-2 text-[10px] text-sky-100 hover:bg-sky-500/10"
                  >
                    Duplicar
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => removeClip(selected.id)}
                    className="rounded-lg border border-rose-400/30 px-1 py-2 text-[10px] text-rose-200 hover:bg-rose-500/10"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {info && !error && (
        <p className="rounded-lg border border-cyan-500/25 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100">
          {info}
        </p>
      )}
      {error && <p className="text-sm text-rose-400">{error}</p>}

      {/* Timeline toolbar */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-[#0e1118] px-3 py-2">
        <span className="text-[11px] uppercase text-slate-500">Herramientas</span>
        <button
          type="button"
          onClick={togglePlay}
          className="rounded-lg bg-cyan-500/15 px-3 py-1.5 text-xs text-cyan-100 hover:bg-cyan-500/25"
        >
          {playing ? 'Pausar' : 'Play'}
        </button>
        <button
          type="button"
          onClick={splitAtPlayhead}
          className="rounded-lg border border-amber-400/30 px-3 py-1.5 text-xs text-amber-100 hover:bg-amber-500/10"
        >
          Cortar en playhead
        </button>
        <button
          type="button"
          onClick={duplicateSelected}
          disabled={!selected}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 disabled:opacity-40"
        >
          Duplicar
        </button>
        <button
          type="button"
          onClick={() => selected && removeClip(selected.id)}
          disabled={!selected}
          className="rounded-lg border border-rose-400/30 px-3 py-1.5 text-xs text-rose-200 disabled:opacity-40"
        >
          Eliminar
        </button>
        <button
          type="button"
          onClick={addTitle}
          className="rounded-lg border border-rose-400/30 px-3 py-1.5 text-xs text-rose-100"
        >
          + Título
        </button>
      </div>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#0e1118]">
        <div className="flex items-center justify-between border-b border-white/8 px-3 py-2">
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Línea de tiempo
          </h2>
          <p className="text-[11px] text-slate-600">
            Playhead rojo · arrastra bloques · borde derecho alarga · Cortar divide el clip
          </p>
        </div>
        <div className="overflow-x-auto">
          <div style={{ width: timelineW, minWidth: '100%' }}>
            <div
              className="relative h-8 cursor-pointer border-b border-white/8 bg-[#0a0c10]"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect()
                const x = e.clientX - rect.left - 96
                seekTo(x / PX_PER_SEC)
              }}
            >
              <div className="absolute inset-y-0 left-0 w-24 border-r border-white/8" />
              {rulerMarks.map((t) => (
                <div
                  key={t}
                  className="absolute top-0 h-full border-l border-white/10"
                  style={{ left: 96 + t * PX_PER_SEC }}
                >
                  <span className="ml-1 font-mono text-[10px] text-slate-500">
                    {formatTime(t)}
                  </span>
                </div>
              ))}
              <div
                className="pointer-events-none absolute top-0 z-20 h-full w-0.5 bg-rose-500"
                style={{ left: 96 + playhead * PX_PER_SEC }}
              />
            </div>

            {tracks.map((track) => (
              <div
                key={track.id}
                className="relative flex h-14 border-b border-white/6"
                onClick={() => setSelectedId(null)}
              >
                <div className="z-10 flex w-24 shrink-0 flex-col justify-center border-r border-white/8 bg-[#0c0e14] px-2">
                  <span className="text-[11px] font-medium text-slate-300">
                    {track.name}
                  </span>
                  <span className="text-[9px] uppercase text-slate-600">
                    {track.kind}
                  </span>
                </div>
                <div
                  className="relative flex-1 bg-[#0a0c12]"
                  onDragOver={(e) => {
                    e.preventDefault()
                    e.dataTransfer.dropEffect = 'copy'
                  }}
                  onDrop={(e) => dropAssetOnTrack(e, track, e.currentTarget)}
                >
                  {rulerMarks.map((t) => (
                    <div
                      key={t}
                      className="absolute inset-y-0 border-l border-white/[0.04]"
                      style={{ left: t * PX_PER_SEC }}
                    />
                  ))}
                  {clips
                    .filter((c) => c.trackId === track.id)
                    .map((clip) => (
                      <div
                        key={clip.id}
                        role="button"
                        tabIndex={0}
                        onPointerDown={(e) => onClipPointerDown(e, clip, 'move')}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedId(clip.id)
                        }}
                        className={[
                          'absolute top-1.5 flex h-11 cursor-grab items-center overflow-hidden rounded border px-2 text-[11px] text-white active:cursor-grabbing',
                          COLORS[clip.kind] || COLORS.video,
                          selectedId === clip.id
                            ? 'ring-2 ring-white/70'
                            : 'opacity-90 hover:opacity-100',
                        ].join(' ')}
                        style={{
                          left: clip.start * PX_PER_SEC,
                          width: Math.max(24, clip.duration * PX_PER_SEC),
                        }}
                        title={clip.label}
                      >
                        <span className="truncate pr-3">{clip.label}</span>
                        {(clip.kind === 'audio' || clip.kind === 'video') && (
                          <span className="absolute bottom-0.5 right-5 text-[9px] text-white/70">
                            {Math.round(clip.volume * 100)}%
                          </span>
                        )}
                        <div
                          className="absolute inset-y-0 right-0 w-2 cursor-ew-resize bg-white/20 hover:bg-white/40"
                          onPointerDown={(e) => onClipPointerDown(e, clip, 'resize')}
                        />
                      </div>
                    ))}
                  <div
                    className="pointer-events-none absolute top-0 z-20 h-full w-0.5 bg-rose-500"
                    style={{ left: playhead * PX_PER_SEC }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {(uploadPct != null || busy) && (
        <div className="rounded-xl border border-white/8 bg-white/[0.03] p-4">
          <ProgressBar
            progress={uploadPct != null ? uploadPct : progress}
            label={
              uploadPct != null
                ? `Subiendo… ${uploadPct}%`
                : detail || 'Editando…'
            }
            etaSeconds={jobQuery.data?.eta_seconds}
          />
        </div>
      )}

      {resultUrl && (
        <section className="space-y-3 rounded-xl border border-cyan-500/25 bg-cyan-500/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-cyan-100">
              Resultado · {resultFormat.toUpperCase()}
            </h2>
            {resultMeta && (
              <span className="text-xs text-slate-500">
                {resultMeta.duration != null && `${resultMeta.duration.toFixed(1)} s`}
                {resultMeta.size != null && ` · ${formatBytes(resultMeta.size)}`}
              </span>
            )}
          </div>
          {resultFormat === 'gif' && (
            <img
              key={resultUrl}
              src={resultUrl}
              alt="GIF exportado"
              className="max-h-[70vh] w-full rounded-xl bg-black object-contain"
            />
          )}
          {(resultFormat === 'mp3' || resultFormat === 'wav') && (
            <audio key={resultUrl} controls autoPlay className="w-full" src={resultUrl} />
          )}
          {(resultFormat === 'mp4' ||
            resultFormat === 'webm' ||
            resultFormat === 'mov' ||
            resultFormat === 'mkv') && (
            <video
              key={resultUrl}
              controls
              autoPlay
              className="max-h-[70vh] w-full rounded-xl bg-black"
              src={resultUrl}
            />
          )}
          {downloadUrl && (
            <a
              href={downloadUrl}
              download
              className="inline-flex text-xs text-cyan-300 underline hover:text-white"
            >
              Descargar {resultFormat.toUpperCase()}
            </a>
          )}
        </section>
      )}
    </div>
  )
}
