import { useQuery } from '@tanstack/react-query'
import { getAnalyticsRanking, getAnalyticsSnapshots } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton, SkeletonCards } from '../components/ui/Skeleton'
import { StatCard } from '../components/ui/StatCard'

export function AnalyticsPage() {
  const rankingQuery = useQuery({
    queryKey: ['analytics', 'ranking'],
    queryFn: () => getAnalyticsRanking(10),
  })

  const snapshotsQuery = useQuery({
    queryKey: ['analytics', 'snapshots'],
    queryFn: () => getAnalyticsSnapshots(20),
  })

  const items = rankingQuery.data?.items ?? []
  const snapshots = snapshotsQuery.data ?? []
  const maxViews = Math.max(1, ...items.map((i) => i.views))

  const totals = snapshots.reduce(
    (acc, s) => ({
      views: acc.views + s.views,
      likes: acc.likes + s.likes,
      comments: acc.comments + s.comments,
    }),
    { views: 0, likes: 0, comments: 0 },
  )

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Analytics"
        description="Ranking de clips y métricas de rendimiento."
      />

      {snapshotsQuery.isLoading ? (
        <SkeletonCards count={3} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label="Vistas" value={totals.views.toLocaleString('es')} accent="cyan" />
          <StatCard label="Likes" value={totals.likes.toLocaleString('es')} accent="teal" />
          <StatCard
            label="Comentarios"
            value={totals.comments.toLocaleString('es')}
            accent="amber"
          />
        </div>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Ranking
        </h2>
        {rankingQuery.isLoading && <Skeleton className="h-40" />}
        {rankingQuery.isError && (
          <p className="text-sm text-rose-400">No se pudo cargar el ranking.</p>
        )}
        {!rankingQuery.isLoading && items.length === 0 && (
          <p className="rounded-xl border border-dashed border-white/10 px-4 py-8 text-center text-sm text-slate-500">
            Sin datos de ranking.
          </p>
        )}
        <ul className="space-y-3">
          {items.map((item, idx) => (
            <li
              key={`${item.clip_id}-${idx}`}
              className="rounded-xl border border-white/8 bg-white/[0.02] px-4 py-3"
            >
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-200">
                  #{idx + 1}{' '}
                  {item.clip_id != null
                    ? `Clip ${item.clip_id}`
                    : item.video_id != null
                      ? `Video ${item.video_id}`
                      : 'Item'}
                </span>
                <span className="text-xs text-slate-500">
                  score {item.score.toFixed(1)} · {item.views} vistas · {item.likes} likes
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-400"
                  style={{ width: `${(item.views / maxViews) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
