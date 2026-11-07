import { CircleHelp, Lock, RotateCw } from 'lucide-react'
import type { Band, CandidateRow, CriterionScore, ScorePayload, Stage } from '@/lib/types'
import { cn } from '@/lib/utils'
import { CriterionList, ScoreBar } from '@/components/ui/criterion-row'
import { ScoreRing } from '@/components/ui/score-ring'
import { StageChip } from '@/components/ui/status-chip'

/** Adapters between API payloads and the kit in components/ui. */

const WORD: Record<Band, string> = { strong: 'Strong', possible: 'Possible', weak: 'Weak' }
const TEXT: Record<Band, string> = { strong: 'text-ok', possible: 'text-warn', weak: 'text-bad' }

/** Band as a word; the dot carries the colour. */
export function BandPill({ band, className }: { band: Band; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-small font-medium', TEXT[band], className)}>
      <span aria-hidden className="size-1.5 rounded-pill bg-current" />
      {WORD[band]}
    </span>
  )
}

/** The score, or an honest statement of why there isn't one (never a fake number). */
export function ScoreBadge({ score, size = 'md', stacked = false }: { score: ScorePayload; size?: 'md' | 'lg'; stacked?: boolean }) {
  return <ScoreRing value={score.total} band={score.band} state={score.state} size={size} stacked={stacked} />
}

export const StageBadge = ({ stage }: { stage: Stage }) => <StageChip stage={stage} />
export const PointsBar = ScoreBar
export const EvidenceList = CriterionList

export function MaskedContacts({ contacts }: { contacts: { email: string; phone: string; masked: boolean } }) {
  return (
    <div className="space-y-0.5 text-small">
      <p className="flex items-center gap-1.5">
        {contacts.masked && <Lock className="size-3.5 text-text-2" aria-hidden />}
        <span className="tnum">{contacts.email}</span>
      </p>
      <p className="tnum">{contacts.phone}</p>
      {contacts.masked && <p className="text-text-2">Contact details unlock when you reach the interview stage.</p>}
    </div>
  )
}

/* TEMPORARY: removed when the ranked list moves to CandidateRow (step 5). */
/** Compact one-line summary of every criterion, for scanning the ranked list. */
export function CriterionChips({ criteria }: { criteria: CriterionScore[] }) {
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Criteria">
      {criteria.map((c) => {
        const none = c.evidence_status === 'no_evidence'
        return (
          <li
            key={c.criterion_id}
            title={none ? 'No evidence found in the CV' : c.unverified ? 'Low confidence: unverified' : c.quote}
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs ring-1',
              none ? 'text-muted-foreground ring-foreground/10' : c.points >= 70 ? 'bg-accent text-accent-foreground ring-primary/25' : 'ring-foreground/15',
            )}
          >
            {c.is_must_have && <span className="font-semibold" aria-label="must-have">*</span>}
            <span className={cn(none && 'line-through decoration-1')}>{c.name}</span>
            <span className="tabular-nums font-medium">{none ? '—' : c.points}</span>
            {c.unverified && <CircleHelp className="size-3" aria-label="Unverified" />}
          </li>
        )
      })}
    </ul>
  )
}

export function RetryHint({ row }: { row: Pick<CandidateRow, 'score'> }) {
  if (row.score.state !== 'failed') return null
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
      <RotateCw className="size-3" aria-hidden /> {row.score.error || 'Please retry.'}
    </span>
  )
}
