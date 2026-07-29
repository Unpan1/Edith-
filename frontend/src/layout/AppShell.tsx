import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { getCreditsBalance } from '../api/saas'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/studio', label: 'Studio' },
  { to: '/compose', label: 'Composición' },
  { to: '/library', label: 'Biblioteca' },
  { to: '/trends', label: 'Tendencias' },
  { to: '/calendar', label: 'Calendario' },
  { to: '/publishing', label: 'Publicación' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/learning', label: 'Aprendizaje' },
  { to: '/automation', label: 'Automatización' },
  { to: '/growth', label: 'Agente' },
  { to: '/credits', label: 'Créditos' },
  { to: '/admin', label: 'Admin' },
] as const

function navClass({ isActive }: { isActive: boolean }) {
  return [
    'block rounded-lg px-3 py-2 text-sm transition-colors',
    isActive
      ? 'bg-cyan-500/15 text-cyan-300 font-medium'
      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200',
  ].join(' ')
}

export function AppShell() {
  const [open, setOpen] = useState(false)
  const creditsQuery = useQuery({
    queryKey: ['credits', 'balance'],
    queryFn: getCreditsBalance,
    staleTime: 30_000,
    retry: 1,
  })

  const balance = creditsQuery.data?.balance

  return (
    <div className="flex min-h-screen">
      {/* Mobile overlay */}
      {open && (
        <button
          type="button"
          aria-label="Cerrar menú"
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-white/8 bg-[#0c0e14]/95 backdrop-blur-xl transition-transform lg:static lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <div className="flex items-center gap-3 border-b border-white/8 px-4 py-5">
          <Link to="/" className="flex items-center gap-3" onClick={() => setOpen(false)}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-teal-600 shadow-lg shadow-cyan-500/20">
              <svg viewBox="0 0 24 24" className="h-5 w-5 text-[#0a0c10]" fill="currentColor">
                <path d="M4 6a2 2 0 012-2h6l2 2h6a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm8 2.5v7l5.5-3.5L12 8.5z" />
              </svg>
            </div>
            <div>
              <p className="font-display text-base font-semibold tracking-tight text-white">
                ClipAI Studio
              </p>
              <p className="text-[10px] uppercase tracking-wide text-slate-500">
                SaaS · Local
              </p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={'end' in item ? item.end : false}
              className={navClass}
              onClick={() => setOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-white/8 bg-[#0c0e14]/80 px-4 py-3 backdrop-blur-xl sm:px-6">
          <button
            type="button"
            className="rounded-lg border border-white/10 bg-white/5 p-2 text-slate-300 lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Abrir menú"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>

          <div className="hidden text-sm text-slate-500 lg:block">
            Panel de control ClipAI
          </div>

          <Link
            to="/credits"
            className="ml-auto inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1.5 text-xs font-medium text-cyan-300 transition hover:bg-cyan-500/20"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            {balance != null ? `${balance.toLocaleString('es')} créditos` : 'Créditos'}
          </Link>
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
