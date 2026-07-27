import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getLibrary } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import { formatDuration } from '../utils/format'

export function LibraryPage() {
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')

  const libraryQuery = useQuery({
    queryKey: ['library', search],
    queryFn: () => getLibrary(search || undefined),
  })

  const data = libraryQuery.data

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Biblioteca"
        description="Videos y clips indexados. Abre el Studio para procesar o edita un clip."
        actions={
          <Link
            to="/studio"
            className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-300"
          >
            Abrir Studio
          </Link>
        }
      />

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          setSearch(q.trim())
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar videos o clips…"
          className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-500/40"
        />
        <button
          type="submit"
          className="rounded-lg bg-white/10 px-4 py-2 text-sm text-slate-200 hover:bg-white/15"
        >
          Buscar
        </button>
      </form>

      {libraryQuery.isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      )}

      {libraryQuery.isError && (
        <p className="text-sm text-rose-400">No se pudo cargar la biblioteca.</p>
      )}

      {data && (
        <div className="grid gap-8 lg:grid-cols-2">
          <section className="space-y-3">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Videos ({data.videos.length})
            </h2>
            {data.videos.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
                Sin videos
              </p>
            ) : (
              <ul className="space-y-2">
                {data.videos.map((v) => (
                  <li
                    key={v.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-200">
                        {v.nombre_original}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatDuration(v.duracion)} · {v.clips_count} clips · {v.estado}
                      </p>
                    </div>
                    <Link
                      to="/studio"
                      className="shrink-0 text-xs text-cyan-400 hover:text-cyan-300"
                    >
                      Studio
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Clips ({data.clips.length})
            </h2>
            {data.clips.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
                Sin clips
              </p>
            ) : (
              <ul className="space-y-2">
                {data.clips.map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-200">
                        {c.titulo_generado || `Clip #${c.id}`}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatDuration(c.duracion)} · score {c.score.toFixed(1)}
                        {c.formato ? ` · ${c.formato}` : ''}
                      </p>
                    </div>
                    <Link
                      to={`/library/clips/${c.id}`}
                      className="shrink-0 text-xs text-cyan-400 hover:text-cyan-300"
                    >
                      Editar
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
