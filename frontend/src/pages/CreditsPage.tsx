import { useQuery } from '@tanstack/react-query'
import { getCreditPlans, getCreditsBalance } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton, SkeletonCards } from '../components/ui/Skeleton'
import { StatCard } from '../components/ui/StatCard'

export function CreditsPage() {
  const balanceQuery = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: getCreditsBalance,
  })

  const plansQuery = useQuery({
    queryKey: ['credits', 'plans'],
    queryFn: getCreditPlans,
  })

  const balance = balanceQuery.data

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Créditos"
        description="Saldo actual y planes disponibles."
      />

      {balanceQuery.isLoading ? (
        <SkeletonCards count={2} />
      ) : balanceQuery.isError ? (
        <p className="text-sm text-rose-400">No se pudo cargar el saldo.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            label="Saldo"
            value={(balance?.balance ?? 0).toLocaleString('es')}
            hint="créditos disponibles"
            accent="cyan"
          />
          <StatCard
            label="Plan actual"
            value={balance?.plan?.nombre ?? 'Sin plan'}
            hint={
              balance?.plan
                ? `${balance.plan.credits_monthly} créditos/mes · $${balance.plan.price}`
                : undefined
            }
            accent="teal"
          />
        </div>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Planes
        </h2>
        {plansQuery.isLoading && (
          <div className="grid gap-4 sm:grid-cols-3">
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
            <Skeleton className="h-36" />
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-3">
          {(plansQuery.data ?? []).map((plan) => (
            <article
              key={plan.id}
              className={[
                'rounded-xl border p-5',
                balance?.plan?.id === plan.id
                  ? 'border-cyan-500/40 bg-cyan-500/10'
                  : 'border-white/8 bg-white/[0.02]',
              ].join(' ')}
            >
              <h3 className="font-display text-lg font-semibold text-white">
                {plan.nombre}
              </h3>
              <p className="mt-2 font-display text-2xl text-cyan-300">
                ${plan.price}
                <span className="text-sm font-sans text-slate-500"> / mes</span>
              </p>
              <p className="mt-2 text-sm text-slate-400">
                {plan.credits_monthly.toLocaleString('es')} créditos mensuales
              </p>
              {!plan.activo && (
                <p className="mt-2 text-xs text-rose-400">Inactivo</p>
              )}
            </article>
          ))}
        </div>
      </section>

      {balance?.ledger && balance.ledger.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
            Movimientos recientes
          </h2>
          <ul className="divide-y divide-white/5 overflow-hidden rounded-xl border border-white/8">
            {balance.ledger.slice(0, 10).map((row) => (
              <li
                key={row.id}
                className="flex items-center justify-between px-4 py-3 text-sm"
              >
                <span className="text-slate-300">{row.reason}</span>
                <span
                  className={
                    row.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }
                >
                  {row.delta >= 0 ? '+' : ''}
                  {row.delta}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
