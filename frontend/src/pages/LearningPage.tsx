import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateInsights, listInsights } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'

export function LearningPage() {
  const qc = useQueryClient()

  const insightsQuery = useQuery({
    queryKey: ['learning', 'insights'],
    queryFn: listInsights,
  })

  const generateMutation = useMutation({
    mutationFn: generateInsights,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['learning', 'insights'] }),
  })

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Aprendizaje"
        description="Insights generados a partir de tu rendimiento."
        actions={
          <button
            type="button"
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
          >
            {generateMutation.isPending ? 'Generando…' : 'Generar insights'}
          </button>
        }
      />

      {insightsQuery.isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      )}

      {insightsQuery.isError && (
        <p className="text-sm text-rose-400">No se pudieron cargar los insights.</p>
      )}

      {!insightsQuery.isLoading && !(insightsQuery.data?.length) && (
        <p className="rounded-xl border border-dashed border-white/10 px-4 py-12 text-center text-sm text-slate-500">
          Sin insights. Genera el primero con el botón de arriba.
        </p>
      )}

      <ul className="space-y-3">
        {(insightsQuery.data ?? []).map((ins) => (
          <li
            key={ins.id}
            className="rounded-xl border border-white/8 bg-white/[0.02] p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">
                  {ins.insight_type}
                </p>
                <h3 className="mt-1 font-medium text-slate-100">{ins.titulo}</h3>
              </div>
              <span className="rounded-full bg-teal-500/15 px-2 py-0.5 text-xs text-teal-300 tabular-nums">
                {ins.score.toFixed(1)}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{ins.detalle}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
