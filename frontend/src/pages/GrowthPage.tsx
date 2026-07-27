import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { runGrowthPlan } from '../api/saas'
import { PageHeader } from '../components/ui/PageHeader'

export function GrowthPage() {
  const [instruction, setInstruction] = useState('')
  const [videoId, setVideoId] = useState('')

  const planMutation = useMutation({
    mutationFn: () =>
      runGrowthPlan({
        instruction: instruction.trim(),
        video_id: Number(videoId),
      }),
  })

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        title="Agente de crecimiento"
        description="Describe tu objetivo y el agente encola un plan multi-plataforma."
      />

      <form
        className="space-y-4 rounded-xl border border-white/8 bg-white/[0.02] p-5"
        onSubmit={(e) => {
          e.preventDefault()
          if (instruction.trim().length >= 3 && videoId) planMutation.mutate()
        }}
      >
        <div>
          <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
            ID del video
          </label>
          <input
            type="number"
            value={videoId}
            onChange={(e) => setVideoId(e.target.value)}
            placeholder="Ej. 1"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            required
          />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Instrucción
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={5}
            placeholder="Ej. Optimiza este video para TikTok y Reels, enfócate en ganchos cortos…"
            className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-500/40"
            required
            minLength={3}
          />
        </div>
        <button
          type="submit"
          disabled={planMutation.isPending || instruction.trim().length < 3 || !videoId}
          className="rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 px-4 py-2 text-sm font-medium text-[#0a0c10] disabled:opacity-40"
        >
          {planMutation.isPending ? 'Encolando…' : 'Ejecutar plan'}
        </button>

        {planMutation.isSuccess && (
          <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-200">
            {planMutation.data.message} · job #{planMutation.data.job_id}
          </p>
        )}
        {planMutation.isError && (
          <p className="text-sm text-rose-400">
            Error al encolar el plan. Revisa el video_id y el backend.
          </p>
        )}
      </form>
    </div>
  )
}
