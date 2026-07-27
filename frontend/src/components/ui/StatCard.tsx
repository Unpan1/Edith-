interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  accent?: 'cyan' | 'teal' | 'amber' | 'rose' | 'slate'
}

const ACCENT: Record<NonNullable<StatCardProps['accent']>, string> = {
  cyan: 'from-cyan-500/15 to-transparent border-cyan-500/20',
  teal: 'from-teal-500/15 to-transparent border-teal-500/20',
  amber: 'from-amber-500/15 to-transparent border-amber-500/20',
  rose: 'from-rose-500/15 to-transparent border-rose-500/20',
  slate: 'from-white/5 to-transparent border-white/10',
}

export function StatCard({ label, value, hint, accent = 'cyan' }: StatCardProps) {
  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-4 ${ACCENT[accent]}`}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className="mt-2 font-display text-2xl font-semibold text-white tabular-nums">
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
