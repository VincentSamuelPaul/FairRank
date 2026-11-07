import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { CriterionScore } from '@/lib/types'
import { cn } from '@/lib/utils'
import { EvidenceQuote } from '@/components/ui/evidence-quote'

export function ScoreBar({ points, className }: { points: number; className?: string }) {
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-pill bg-surface-2', className)} role="presentation">
      <div className="h-full rounded-pill bg-text-1/70" style={{ width: `${Math.max(0, Math.min(100, points))}%` }} />
    </div>
  )
}

const LONG = 90

/** Criterion name, must-have marker, score bar, then its evidence. Collapsed shows one line; expand for the full quote. */
export function CriterionRow({ criterion: c, active = false, onSelect, defaultExpanded = false }: { criterion: CriterionScore; active?: boolean; onSelect?: (c: CriterionScore) => void; defaultExpanded?: boolean }) {
  const none = c.evidence_status === 'no_evidence'
  const [open, setOpen] = useState(defaultExpanded)
  const long = !none && c.quote.length > LONG
  return (
    <li id={`crit-${c.criterion_id}`} className={cn('space-y-2 p-4', active && 'bg-surface-2')}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-body font-medium">
          {c.name}
          <span className="ml-2 whitespace-nowrap text-micro font-medium uppercase text-text-2">{c.is_must_have ? 'Must-have' : 'Nice-to-have'}</span>
        </p>
        <span className="tnum text-body font-medium">{none ? '—' : c.points}</span>
      </div>
      <ScoreBar points={none ? 0 : c.points} />
      <EvidenceQuote
        criterion={c.name}
        quote={c.quote}
        status={c.evidence_status}
        unverified={c.unverified}
        clamp={long && !open}
        active={active}
        showCriterion={false}
        onSelect={onSelect && !none && c.span ? () => onSelect(c) : undefined}
      />
      {long && (
        <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="inline-flex min-h-7 items-center gap-1 text-small text-text-2 hover:text-text-1">
          <ChevronDown className={cn('size-3.5 transition-transform duration-(--dur-fast)', open && 'rotate-180')} aria-hidden />
          {open ? 'Show less' : 'Show full quote'}
        </button>
      )}
      {c.rationale && !none && <p className="text-small text-text-2">{c.rationale}</p>}
    </li>
  )
}

export function CriterionList({ criteria, activeId, onSelect }: { criteria: CriterionScore[]; activeId?: number | null; onSelect?: (c: CriterionScore) => void }) {
  return (
    <ul className="divide-y overflow-hidden rounded-card border bg-surface-1">
      {criteria.map((c) => (
        <CriterionRow key={c.criterion_id} criterion={c} active={activeId === c.criterion_id} onSelect={onSelect} />
      ))}
    </ul>
  )
}
