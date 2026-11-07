import { STAGES, stageLabel } from '@/lib/format'
import type { Stage } from '@/lib/types'

const FLOW = STAGES.filter((s) => s.key !== 'rejected')

/** Seven small segments (Sourced to Joined) filled up to the furthest stage any CV has reached, in the single `--signal` hue (empty segments 8% white). */
export function PipelineProgress({ furthest }: { furthest: Stage | null }) {
  const at = furthest ? FLOW.findIndex((s) => s.key === furthest) : -1
  return (
    <div className="space-y-1.5">
      <div role="img" aria-label={furthest ? `Furthest stage reached: ${stageLabel(furthest)}` : 'No CV has entered the pipeline yet'} className="flex gap-0.5">
        {FLOW.map((s, i) => (
          <span key={s.key} className={i <= at ? 'h-1.5 flex-1 rounded-pill bg-signal' : 'h-1.5 flex-1 rounded-pill bg-track'} />
        ))}
      </div>
      <p className="text-micro text-text-2">{furthest ? `Furthest: ${stageLabel(furthest)}` : 'Nothing in the pipeline yet'}</p>
    </div>
  )
}
