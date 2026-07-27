import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getCalendarMonth } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import type { ScheduledPost } from '../types/saas'
import { PLATFORM_LABELS } from '../types/saas'

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate()
}

/** Monday-based offset for day 1 */
function startOffset(year: number, month: number) {
  const d = new Date(year, month - 1, 1).getDay()
  return d === 0 ? 6 : d - 1
}

function postsOnDay(posts: ScheduledPost[], year: number, month: number, day: number) {
  return posts.filter((p) => {
    const raw = p.scheduled_at || p.published_at || p.fecha
    if (!raw) return false
    const dt = new Date(raw)
    return (
      dt.getFullYear() === year &&
      dt.getMonth() + 1 === month &&
      dt.getDate() === day
    )
  })
}

export function CalendarPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)

  const calQuery = useQuery({
    queryKey: ['calendar', year, month],
    queryFn: () => getCalendarMonth(year, month),
  })

  const posts = calQuery.data?.posts ?? []
  const totalDays = daysInMonth(year, month)
  const offset = startOffset(year, month)

  const cells = useMemo(() => {
    const empty = Array.from({ length: offset }, () => null as number | null)
    const days = Array.from({ length: totalDays }, (_, i) => i + 1)
    return [...empty, ...days]
  }, [offset, totalDays])

  const monthLabel = new Date(year, month - 1).toLocaleDateString('es', {
    month: 'long',
    year: 'numeric',
  })

  function prevMonth() {
    if (month === 1) {
      setMonth(12)
      setYear((y) => y - 1)
    } else setMonth((m) => m - 1)
  }

  function nextMonth() {
    if (month === 12) {
      setMonth(1)
      setYear((y) => y + 1)
    } else setMonth((m) => m + 1)
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHeader
        title="Calendario"
        description="Publicaciones programadas del mes."
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={prevMonth}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300"
            >
              ←
            </button>
            <span className="min-w-[10rem] text-center text-sm capitalize text-slate-200">
              {monthLabel}
            </span>
            <button
              type="button"
              onClick={nextMonth}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300"
            >
              →
            </button>
          </div>
        }
      />

      {calQuery.isLoading ? (
        <Skeleton className="h-96" />
      ) : calQuery.isError ? (
        <p className="text-sm text-rose-400">No se pudo cargar el calendario.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/8 bg-white/[0.02]">
          <div className="grid grid-cols-7 border-b border-white/8">
            {WEEKDAYS.map((d) => (
              <div
                key={d}
                className="px-2 py-2 text-center text-[11px] font-medium uppercase tracking-wider text-slate-500"
              >
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((day, i) => {
              const dayPosts = day ? postsOnDay(posts, year, month, day) : []
              return (
                <div
                  key={i}
                  className="min-h-[5.5rem] border-b border-r border-white/5 p-1.5 sm:min-h-[6.5rem]"
                >
                  {day && (
                    <>
                      <span className="text-xs text-slate-500">{day}</span>
                      <div className="mt-1 space-y-0.5">
                        {dayPosts.slice(0, 3).map((p) => (
                          <div
                            key={p.id}
                            className="truncate rounded bg-cyan-500/15 px-1 py-0.5 text-[10px] text-cyan-300"
                            title={p.titulo || PLATFORM_LABELS[p.platform]}
                          >
                            {PLATFORM_LABELS[p.platform]}
                          </div>
                        ))}
                        {dayPosts.length > 3 && (
                          <span className="text-[10px] text-slate-500">
                            +{dayPosts.length - 3}
                          </span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
