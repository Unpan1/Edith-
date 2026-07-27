import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  connectAccount,
  createPost,
  deletePost,
  listAccounts,
  listPosts,
} from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import type { Platform, PostStatus } from '../types/saas'
import { PLATFORM_LABELS, POST_STATUS_LABELS } from '../types/saas'

const PLATFORMS = Object.keys(PLATFORM_LABELS) as Platform[]

export function PublishingPage() {
  const qc = useQueryClient()
  const [platform, setPlatform] = useState<Platform>('tiktok')
  const [titulo, setTitulo] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [clipId, setClipId] = useState('')
  const [status, setStatus] = useState<PostStatus>('draft')
  const [handle, setHandle] = useState('')
  const [connectPlatform, setConnectPlatform] = useState<Platform>('tiktok')

  const postsQuery = useQuery({
    queryKey: ['publishing', 'posts'],
    queryFn: () => listPosts(),
  })

  const accountsQuery = useQuery({
    queryKey: ['publishing', 'accounts'],
    queryFn: listAccounts,
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createPost({
        platform,
        titulo: titulo || null,
        descripcion: descripcion || null,
        clip_id: clipId ? Number(clipId) : null,
        status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['publishing', 'posts'] })
      setTitulo('')
      setDescripcion('')
      setClipId('')
    },
  })

  const connectMutation = useMutation({
    mutationFn: () => connectAccount(connectPlatform, handle),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['publishing', 'accounts'] })
      setHandle('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deletePost(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['publishing', 'posts'] }),
  })

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Publicación"
        description="Conecta cuentas (stub) y gestiona borradores o posts programados."
      />

      <div className="grid gap-8 lg:grid-cols-2">
        <section className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Cuentas sociales
          </h2>
          {accountsQuery.isLoading && <Skeleton className="h-20" />}
          <ul className="space-y-2">
            {(accountsQuery.data ?? []).map((a) => (
              <li
                key={a.id}
                className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3 text-sm"
              >
                <span className="text-slate-200">
                  {PLATFORM_LABELS[a.platform]}
                  {a.handle ? ` · @${a.handle}` : ''}
                </span>
                <span
                  className={
                    a.connected
                      ? 'text-xs text-emerald-400'
                      : 'text-xs text-slate-500'
                  }
                >
                  {a.connected ? 'Conectada' : 'Desconectada'}
                </span>
              </li>
            ))}
            {!accountsQuery.isLoading && !(accountsQuery.data?.length) && (
              <p className="text-sm text-slate-500">Ninguna cuenta conectada.</p>
            )}
          </ul>

          <form
            className="space-y-3 rounded-xl border border-white/8 bg-white/[0.02] p-4"
            onSubmit={(e) => {
              e.preventDefault()
              if (handle.trim()) connectMutation.mutate()
            }}
          >
            <p className="text-xs text-slate-500">Conectar cuenta (stub OAuth)</p>
            <select
              value={connectPlatform}
              onChange={(e) => setConnectPlatform(e.target.value as Platform)}
              className="w-full rounded-lg border border-white/10 bg-[#0c0e14] px-3 py-2 text-sm text-slate-200"
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {PLATFORM_LABELS[p]}
                </option>
              ))}
            </select>
            <input
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="@usuario"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            />
            <button
              type="submit"
              disabled={connectMutation.isPending || !handle.trim()}
              className="rounded-lg bg-white/10 px-4 py-2 text-sm text-slate-200 disabled:opacity-40"
            >
              Conectar
            </button>
          </form>
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Nuevo post
          </h2>
          <form
            className="space-y-3 rounded-xl border border-white/8 bg-white/[0.02] p-4"
            onSubmit={(e) => {
              e.preventDefault()
              createMutation.mutate()
            }}
          >
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value as Platform)}
              className="w-full rounded-lg border border-white/10 bg-[#0c0e14] px-3 py-2 text-sm text-slate-200"
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {PLATFORM_LABELS[p]}
                </option>
              ))}
            </select>
            <input
              value={clipId}
              onChange={(e) => setClipId(e.target.value)}
              placeholder="ID del clip (opcional)"
              type="number"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            />
            <input
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              placeholder="Título"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            />
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Descripción"
              rows={3}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as PostStatus)}
              className="w-full rounded-lg border border-white/10 bg-[#0c0e14] px-3 py-2 text-sm text-slate-200"
            >
              {(Object.keys(POST_STATUS_LABELS) as PostStatus[]).map((s) => (
                <option key={s} value={s}>
                  {POST_STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
            >
              Crear post
            </button>
            {createMutation.isError && (
              <p className="text-xs text-rose-400">Error al crear el post.</p>
            )}
          </form>
        </section>
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Posts ({postsQuery.data?.length ?? 0})
        </h2>
        {postsQuery.isLoading && <Skeleton className="h-24" />}
        <ul className="space-y-2">
          {(postsQuery.data ?? []).map((p) => (
            <li
              key={p.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-200">
                  {p.titulo || `Post #${p.id}`}
                </p>
                <p className="text-xs text-slate-500">
                  {PLATFORM_LABELS[p.platform]} · {POST_STATUS_LABELS[p.status]}
                  {p.clip_id != null ? ` · clip ${p.clip_id}` : ''}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  if (confirm('¿Eliminar este post?')) deleteMutation.mutate(p.id)
                }}
                className="text-xs text-rose-400 hover:text-rose-300"
              >
                Eliminar
              </button>
            </li>
          ))}
          {!postsQuery.isLoading && !(postsQuery.data?.length) && (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
              No hay posts todavía.
            </p>
          )}
        </ul>
      </section>
    </div>
  )
}
