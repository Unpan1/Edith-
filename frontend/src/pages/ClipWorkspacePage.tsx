import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  createThumbnail,
  generateClipContent,
  getClipContent,
  getClipEditor,
  listThumbnails,
  updateClipEditor,
} from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import { formatDuration } from '../utils/format'

export function ClipWorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const clipId = Number(id)
  const qc = useQueryClient()

  const [titulo, setTitulo] = useState('')
  const [caption, setCaption] = useState('')
  const [overlay, setOverlay] = useState('')

  const editorQuery = useQuery({
    queryKey: ['editor', clipId],
    queryFn: () => getClipEditor(clipId),
    enabled: Number.isFinite(clipId) && clipId > 0,
  })

  const contentQuery = useQuery({
    queryKey: ['content', clipId],
    queryFn: () => getClipContent(clipId),
    enabled: Number.isFinite(clipId) && clipId > 0,
    retry: false,
  })

  const thumbsQuery = useQuery({
    queryKey: ['thumbnails', clipId],
    queryFn: () => listThumbnails(clipId),
    enabled: Number.isFinite(clipId) && clipId > 0,
  })

  useEffect(() => {
    if (editorQuery.data) {
      setTitulo(editorQuery.data.titulo_generado ?? '')
      setCaption(editorQuery.data.caption_texto ?? '')
    }
  }, [editorQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      updateClipEditor(clipId, {
        titulo_generado: titulo || null,
        caption_texto: caption || null,
      }),
    onSuccess: (data) => {
      qc.setQueryData(['editor', clipId], data)
    },
  })

  const generateMutation = useMutation({
    mutationFn: () => generateClipContent(clipId),
    onSuccess: (data) => {
      qc.setQueryData(['content', clipId], data)
      if (data.titles[0]) setTitulo(data.titles[0])
      if (data.descriptions[0]) setCaption(data.descriptions[0])
    },
  })

  const thumbMutation = useMutation({
    mutationFn: () =>
      createThumbnail(clipId, overlay.trim() ? { texto_overlay: overlay.trim() } : undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['thumbnails', clipId] }),
  })

  if (!Number.isFinite(clipId) || clipId <= 0) {
    return <p className="text-sm text-rose-400">ID de clip inválido.</p>
  }

  const editor = editorQuery.data
  const content = contentQuery.data

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHeader
        title={editor?.titulo_generado || `Clip #${clipId}`}
        description="Edita metadatos, genera contenido IA y miniaturas."
        actions={
          <Link to="/library" className="text-sm text-cyan-400 hover:text-cyan-300">
            ← Biblioteca
          </Link>
        }
      />

      {editorQuery.isLoading && <Skeleton className="h-40" />}
      {editorQuery.isError && (
        <p className="text-sm text-rose-400">No se pudo cargar el clip.</p>
      )}

      {editor && (
        <>
          <p className="text-sm text-slate-500">
            {formatDuration(editor.duracion)}
            {editor.formato ? ` · ${editor.formato}` : ''}
            {' · '}
            {editor.inicio.toFixed(1)}s – {editor.fin.toFixed(1)}s
          </p>

          <form
            className="space-y-4 rounded-xl border border-white/8 bg-white/[0.02] p-5"
            onSubmit={(e) => {
              e.preventDefault()
              saveMutation.mutate()
            }}
          >
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Título
              </label>
              <input
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
              />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Descripción / caption
              </label>
              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                rows={4}
                className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={saveMutation.isPending}
                className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
              >
                Guardar
              </button>
              <button
                type="button"
                onClick={() => generateMutation.mutate()}
                disabled={generateMutation.isPending}
                className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-300 disabled:opacity-40"
              >
                {generateMutation.isPending ? 'Generando…' : 'Generar con IA'}
              </button>
            </div>
            {saveMutation.isSuccess && (
              <p className="text-xs text-emerald-400">Guardado correctamente.</p>
            )}
          </form>

          {content && (
            <section className="space-y-4 rounded-xl border border-white/8 bg-white/[0.02] p-5">
              <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
                Contenido IA
              </h2>
              {content.titles.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500">Títulos</p>
                  <ul className="mt-1 space-y-1">
                    {content.titles.map((t) => (
                      <li key={t}>
                        <button
                          type="button"
                          onClick={() => setTitulo(t)}
                          className="text-left text-sm text-slate-300 hover:text-cyan-300"
                        >
                          {t}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {content.descriptions.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500">Descripciones</p>
                  <ul className="mt-1 space-y-1">
                    {content.descriptions.map((d) => (
                      <li key={d}>
                        <button
                          type="button"
                          onClick={() => setCaption(d)}
                          className="text-left text-sm text-slate-400 hover:text-cyan-300"
                        >
                          {d}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {content.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {content.hashtags.map((h) => (
                    <span
                      key={h}
                      className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-cyan-300/80"
                    >
                      #{h.replace(/^#/, '')}
                    </span>
                  ))}
                </div>
              )}
            </section>
          )}

          <section className="space-y-4 rounded-xl border border-white/8 bg-white/[0.02] p-5">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Miniaturas
            </h2>
            {thumbsQuery.isLoading && <Skeleton className="h-24" />}
            <ul className="space-y-2">
              {(thumbsQuery.data ?? []).map((th) => (
                <li key={th.id} className="text-sm text-slate-400">
                  #{th.id}
                  {th.texto_overlay ? ` · ${th.texto_overlay}` : ''}
                  {th.es_principal ? ' · principal' : ''}
                </li>
              ))}
              {!thumbsQuery.isLoading && !(thumbsQuery.data?.length) && (
                <p className="text-sm text-slate-500">Sin miniaturas.</p>
              )}
            </ul>
            <div className="flex flex-wrap gap-2">
              <input
                value={overlay}
                onChange={(e) => setOverlay(e.target.value)}
                placeholder="Texto overlay (opcional)"
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
              />
              <button
                type="button"
                onClick={() => thumbMutation.mutate()}
                disabled={thumbMutation.isPending}
                className="rounded-lg bg-white/10 px-4 py-2 text-sm text-slate-200 disabled:opacity-40"
              >
                Crear miniatura
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
