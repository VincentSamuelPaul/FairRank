import { STAGES, stageLabel } from '@/lib/format'
import type { Stage } from '@/lib/types'

const FLOW = STAGES.filter((s) => s.key !== 'rejected')

/** Seven small segments (Sourced to Joined) filled up to the furthest stage any CV has reached, each in its stage hue. */
export function PipelineProgress({ furthest }: { furthest: Stage | null }) {
  const at = furthest ? FLOW.findIndex((s) => s.key === furthest) : -1
  return (
    <div className="space-y-1.5">
      <div role="img" aria-label={furthest ? `Furthest stage reached: ${stageLabel(furthest)}` : 'No CV has entered the pipeline yet'} className="flex gap-0.5">
        {FLOW.map((s, i) => (
          <span key={s.key} style={{ '--h': `var(--stage-${s.key})` } as React.CSSProperties} className={i <= at ? 'h-1.5 flex-1 rounded-pill bg-(--h)' : 'h-1.5 flex-1 rounded-pill bg-surface-2'} />
        ))}
      </div>
      <p className="text-micro text-text-2">{furthest ? `Furthest: ${stageLabel(furthest)}` : 'Nothing in the pipeline yet'}</p>
    </div>
  )
}
