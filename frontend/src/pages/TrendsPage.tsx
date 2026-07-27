import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getTrends } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'

export function TrendsPage() {
  const [category, setCategory] = useState('')
  const [country, setCountry] = useState('')
  const [filters, setFilters] = useState<{ category?: string; country?: string }>({})

  const trendsQuery = useQuery({
    queryKey: ['trends', filters],
    queryFn: () => getTrends(filters),
  })

  const items = trendsQuery.data?.items ?? []

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Tendencias"
        description="Oportunidades de contenido por categoría y país."
      />

      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          setFilters({
            category: category.trim() || undefined,
            country: country.trim() || undefined,
          })
        }}
      >
        <input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="Categoría"
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-500/40"
        />
        <input
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          placeholder="País (ej. MX, US)"
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-500/40"
        />
        <button
          type="submit"
          className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10]"
        >
          Filtrar
        </button>
      </form>

      {trendsQuery.isLoading && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      )}

      {trendsQuery.isError && (
        <p className="text-sm text-rose-400">No se pudieron cargar las tendencias.</p>
      )}

      {!trendsQuery.isLoading && items.length === 0 && (
        <p className="rounded-xl border border-dashed border-white/10 px-4 py-12 text-center text-sm text-slate-500">
          No hay reportes de tendencias todavía.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((t) => (
          <article
            key={t.id}
            className="rounded-xl border border-white/8 bg-white/[0.02] p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-medium text-slate-100">{t.title}</h3>
              <span className="shrink-0 rounded-full bg-teal-500/15 px-2 py-0.5 text-xs font-medium text-teal-300 tabular-nums">
                {t.opportunity_score.toFixed(0)}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {t.category} · {t.country} · score {t.score.toFixed(1)}
            </p>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-400"
                style={{ width: `${Math.min(100, t.opportunity_score)}%` }}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
