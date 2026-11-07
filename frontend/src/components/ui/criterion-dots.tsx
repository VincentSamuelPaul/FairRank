import type { CriterionScore } from '@/lib/types'
import { cn } from '@/lib/utils'

/** One dot per criterion: filled = a verified quote exists, hollow = none. The sentence beside it says the same in words. */
export function CriterionDots({ criteria }: { criteria: CriterionScore[] }) {
  const found = criteria.filter((c) => c.evidence_status === 'verified').length
  return (
    <p className="flex items-center gap-2.5 text-small text-text-2">
      <span className="flex gap-1" role="img" aria-label={`Evidence found for ${found} of ${criteria.length} criteria`}>
        {criteria.map((c) => (
          <span
            key={c.criterion_id}
            title={`${c.name}: ${c.evidence_status === 'verified' ? 'evidence found' : 'no evidence found'}`}
            className={cn('size-2 rounded-pill border', c.evidence_status === 'verified' ? 'border-text-1 bg-text-1' : 'border-text-3')}
          />
        ))}
      </span>
      <span className="tnum">{found} of {criteria.length} criteria have evidence</span>
    </p>
  )
}
