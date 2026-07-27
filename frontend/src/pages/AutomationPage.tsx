import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAutomationSettings,
  updateAutomationSettings,
} from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'
import { Skeleton } from '../components/ui/Skeleton'
import type { AutomationSettings } from '../types/saas'

function Toggle({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string
  description: string
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-white/8 bg-white/[0.02] px-4 py-4">
      <div>
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="mt-1 text-xs text-slate-500">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          'relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors',
          checked ? 'bg-cyan-500' : 'bg-white/10',
          disabled ? 'opacity-40' : '',
        ].join(' ')}
      >
        <span
          className={[
            'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform',
            checked ? 'translate-x-5' : '',
          ].join(' ')}
        />
      </button>
    </label>
  )
}

export function AutomationPage() {
  const qc = useQueryClient()

  const settingsQuery = useQuery({
    queryKey: ['automation', 'settings'],
    queryFn: getAutomationSettings,
  })

  const updateMutation = useMutation({
    mutationFn: updateAutomationSettings,
    onSuccess: (data) => {
      qc.setQueryData(['automation', 'settings'], data)
    },
  })

  function patch(partial: Partial<AutomationSettings>) {
    updateMutation.mutate(partial)
  }

  const s = settingsQuery.data

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        title="Automatización"
        description="Activa o desactiva flujos automáticos tras el procesamiento."
      />

      {settingsQuery.isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      )}

      {settingsQuery.isError && (
        <p className="text-sm text-rose-400">No se pudieron cargar los ajustes.</p>
      )}

      {s && (
        <div className="space-y-3">
          <Toggle
            label="Enriquecer tras procesar"
            description="Genera títulos, descripciones y hashtags automáticamente."
            checked={s.enrich_after_process}
            disabled={updateMutation.isPending}
            onChange={(v) => patch({ enrich_after_process: v })}
          />
          <Toggle
            label="Miniaturas automáticas"
            description="Crea miniaturas al finalizar los clips."
            checked={s.auto_thumbnails}
            disabled={updateMutation.isPending}
            onChange={(v) => patch({ auto_thumbnails: v })}
          />
          <Toggle
            label="Programar stubs"
            description="Crea borradores de publicación al completar el procesamiento."
            checked={s.auto_schedule_stubs}
            disabled={updateMutation.isPending}
            onChange={(v) => patch({ auto_schedule_stubs: v })}
          />
        </div>
      )}
    </div>
  )
}
