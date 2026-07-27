import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDashboardStats, listJobs } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton, SkeletonCards } from '../components/ui/Skeleton'
import { StatCard } from '../components/ui/StatCard'

export function DashboardPage() {
  const statsQuery = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: getDashboardStats,
  })

  const jobsQuery = useQuery({
    queryKey: ['jobs', 'recent'],
    queryFn: () => listJobs(undefined, 8),
  })

  const s = statsQuery.data

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Dashboard"
        description="Resumen de producción, tiempo ahorrado, publicaciones y créditos."
        actions={
          <Link
            to="/studio"
            className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10]"
          >
            Ir al Studio
          </Link>
        }
      />

      {statsQuery.isLoading ? (
        <SkeletonCards count={8} />
      ) : statsQuery.isError ? (
        <p className="text-sm text-rose-400">
          No se pudieron cargar las estadísticas. ¿Está el backend en :8000?
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Videos" value={s?.videos ?? 0} hint={`${s?.videos_completed ?? 0} completados`} accent="cyan" />
          <StatCard label="Clips" value={s?.clips ?? 0} hint={`${s?.minutes_processed ?? 0} min procesados`} accent="teal" />
          <StatCard label="Tiempo ahorrado" value={`${s?.time_saved_hours ?? 0}h`} hint="vs edición manual" accent="amber" />
          <StatCard label="Créditos" value={s?.credits_balance ?? 0} hint={`${s?.credits_used_month ?? 0} usados este mes`} accent="slate" />
          <StatCard label="En cola" value={s?.jobs_queued ?? 0} hint={`${s?.jobs_processing ?? 0} procesando`} accent="cyan" />
          <StatCard label="Programados" value={s?.scheduled_posts ?? 0} accent="teal" />
          <StatCard label="Publicados" value={s?.published_posts ?? 0} accent="amber" />
          <StatCard label="Notificaciones" value={s?.notifications_unread ?? 0} accent="slate" />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Últimos clips
            </h2>
            <Link to="/library" className="text-xs text-cyan-400 hover:underline">
              Ver biblioteca
            </Link>
          </div>
          {!s?.recent_clips?.length ? (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
              Aún no hay clips. Genéralos en el Studio.
            </p>
          ) : (
            <ul className="divide-y divide-white/5 overflow-hidden rounded-xl border border-white/8 bg-white/[0.02]">
              {s.recent_clips.map((c) => (
                <li key={c.id}>
                  <Link
                    to={`/library/clips/${c.id}`}
                    className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm transition hover:bg-white/[0.03]"
                  >
                    <span className="line-clamp-1 font-medium text-slate-200">
                      {c.titulo || `Clip #${c.id}`}
                    </span>
                    <span className="text-xs text-slate-500">
                      {c.formato?.replace(/_/g, ' ') || '—'} · score {c.score.toFixed(1)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Jobs / procesamiento
          </h2>
          {jobsQuery.isLoading && (
            <div className="space-y-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          )}
          {jobsQuery.data && jobsQuery.data.length === 0 && (
            <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
              Sin jobs en cola
            </p>
          )}
          {jobsQuery.data && jobsQuery.data.length > 0 && (
            <ul className="divide-y divide-white/5 overflow-hidden rounded-xl border border-white/8 bg-white/[0.02]">
              {jobsQuery.data.map((job) => (
                <li
                  key={job.id}
                  className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm"
                >
                  <div>
                    <span className="font-medium text-slate-200">{job.tipo}</span>
                    <span className="ml-2 text-xs text-slate-500">#{job.id}</span>
                  </div>
                  <span
                    className={[
                      'rounded-full px-2 py-0.5 text-xs capitalize',
                      job.status === 'completed'
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : job.status === 'failed'
                          ? 'bg-rose-500/15 text-rose-300'
                          : 'bg-cyan-500/15 text-cyan-300',
                    ].join(' ')}
                  >
                    {job.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
