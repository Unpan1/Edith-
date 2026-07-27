import { useQuery } from '@tanstack/react-query'
import { getAdminOverview } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton, SkeletonCards } from '../components/ui/Skeleton'
import { StatCard } from '../components/ui/StatCard'

export function AdminPage() {
  const overviewQuery = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: getAdminOverview,
  })

  const data = overviewQuery.data
  const stats = data?.stats

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Admin"
        description="Vista general del sistema: usuarios, jobs y métricas."
      />

      {overviewQuery.isLoading ? (
        <SkeletonCards count={6} />
      ) : overviewQuery.isError ? (
        <p className="text-sm text-rose-400">No se pudo cargar el overview.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard label="Usuarios" value={stats?.users ?? 0} accent="cyan" />
          <StatCard label="Videos" value={stats?.videos ?? 0} accent="teal" />
          <StatCard label="Clips" value={stats?.clips ?? 0} accent="amber" />
          <StatCard label="Jobs" value={stats?.jobs ?? 0} accent="slate" />
          <StatCard
            label="Posts programados"
            value={stats?.scheduled_posts ?? 0}
            accent="cyan"
          />
          <StatCard label="Planes" value={stats?.plans ?? 0} accent="teal" />
        </div>
      )}

      {data && (
        <div className="grid gap-8 lg:grid-cols-2">
          <section className="space-y-3">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Usuarios
            </h2>
            {data.users.length === 0 ? (
              <p className="text-sm text-slate-500">Sin usuarios.</p>
            ) : (
              <ul className="divide-y divide-white/5 overflow-hidden rounded-xl border border-white/8">
                {data.users.map((u) => (
                  <li key={u.id} className="px-4 py-3 text-sm">
                    <p className="font-medium text-slate-200">{u.nombre}</p>
                    <p className="text-xs text-slate-500">{u.email}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
              Jobs recientes
            </h2>
            {overviewQuery.isLoading && <Skeleton className="h-32" />}
            {data.recent_jobs.length === 0 ? (
              <p className="text-sm text-slate-500">Sin jobs.</p>
            ) : (
              <ul className="divide-y divide-white/5 overflow-hidden rounded-xl border border-white/8">
                {data.recent_jobs.map((j) => (
                  <li
                    key={j.id}
                    className="flex items-center justify-between px-4 py-3 text-sm"
                  >
                    <span className="text-slate-200">
                      {j.tipo} <span className="text-slate-500">#{j.id}</span>
                    </span>
                    <span className="text-xs capitalize text-slate-400">{j.status}</span>
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
