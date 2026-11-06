import { AlertTriangle, Check, CircleHelp, Lock, RotateCw, ScanLine } from 'lucide-react'
import type { Band, CandidateRow, CriterionScore, ScorePayload, Stage } from '@/lib/types'
import { stageLabel } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Spinner } from '@/components/states'

const BAND: Record<Band, { label: string; pill: string }> = {
  strong: { label: 'Strong', pill: 'bg-primary text-primary-foreground' },
  possible: { label: 'Possible', pill: 'bg-accent text-accent-foreground ring-1 ring-primary/30' },
  weak: { label: 'Weak', pill: 'bg-muted text-muted-foreground' },
}

export function BandPill({ band, className }: { band: Band; className?: string }) {
  return (
    <span className={cn('inline-flex h-5 items-center rounded-full px-2 text-xs font-medium', BAND[band].pill, className)}>
      {BAND[band].label}
    </span>
  )
}

/** The score, or an honest statement of why there isn't one (never a fake number). */
export function ScoreBadge({ score, size = 'md' }: { score: ScorePayload; size?: 'md' | 'lg' }) {
  const big = size === 'lg'
  if (score.state === 'scored' && score.total !== null && score.band) {
    return (
      <div className="flex items-center gap-2" aria-label={`Score ${Math.round(score.total)} out of 100, ${BAND[score.band].label}`}>
        <span className={cn('font-semibold tabular-nums tracking-tight', big ? 'text-4xl' : 'text-2xl')}>{Math.round(score.total)}</span>
        <BandPill band={score.band} />
      </div>
    )
  }
  const states: Record<string, { icon: React.ReactNode; text: string; tone?: string }> = {
    needs_manual_review: { icon: <ScanLine className="size-4" />, text: 'Needs manual review' },
    failed: { icon: <AlertTriangle className="size-4" />, text: 'Scoring failed', tone: 'text-destructive' },
    cv_failed: { icon: <AlertTriangle className="size-4" />, text: 'File unreadable', tone: 'text-destructive' },
    processing: { icon: <Spinner />, text: 'Processing' },
    pending: { icon: <Spinner />, text: 'Scoring' },
    no_scorecard: { icon: <CircleHelp className="size-4" />, text: 'No scorecard yet' },
  }
  const s = states[score.state] ?? states.pending
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-lg border border-dashed px-2 py-1 text-sm', s.tone ?? 'text-muted-foreground')}>
      {s.icon}
      {s.text}
    </span>
  )
}

export function StageBadge({ stage }: { stage: Stage }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 items-center rounded-full px-2 text-xs font-medium ring-1 ring-foreground/10',
        stage === 'rejected' ? 'bg-muted text-muted-foreground line-through decoration-1' : 'bg-background text-foreground',
      )}
    >
      {stageLabel(stage)}
    </span>
  )
}

export function PointsBar({ points }: { points: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" role="presentation">
      <div className="h-full rounded-full bg-primary" style={{ width: `${points}%` }} />
    </div>
  )
}

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

/** Full evidence: every criterion with its verified quote, or an explicit "No evidence found". */
export function EvidenceList({
  criteria,
  activeId,
  onSelect,
}: {
  criteria: CriterionScore[]
  activeId?: number | null
  onSelect?: (c: CriterionScore) => void
}) {
  return (
    <ul className="divide-y rounded-xl border">
      {criteria.map((c) => {
        const none = c.evidence_status === 'no_evidence'
        const clickable = !!onSelect && !none && !!c.span
        return (
          <li key={c.criterion_id} className={cn('space-y-2 p-3', activeId === c.criterion_id && 'bg-accent/50')}>
            <div className="flex items-baseline justify-between gap-3">
              <p className="text-sm font-medium">
                {c.name}
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  {c.is_must_have ? 'Must-have' : 'Nice-to-have'} · weight {c.weight}
                </span>
              </p>
              <span className="text-sm font-semibold tabular-nums">{none ? '—' : c.points}</span>
            </div>
            <PointsBar points={none ? 0 : c.points} />
            {none ? (
              <p className="text-sm text-muted-foreground">No evidence found in the CV.</p>
            ) : (
              <blockquote className="border-l-2 border-primary/50 pl-3 text-sm">
                {clickable ? (
                  <button type="button" className="text-left hover:underline" onClick={() => onSelect?.(c)}>
                    “{c.quote}”
                  </button>
                ) : (
                  <>“{c.quote}”</>
                )}
              </blockquote>
            )}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {!none && (
                <span className="inline-flex items-center gap-1">
                  <Check className="size-3 text-primary" aria-hidden /> Quote verified in CV
                </span>
              )}
              {c.unverified && (
                <span className="inline-flex items-center gap-1 text-foreground">
                  <CircleHelp className="size-3" aria-hidden /> Unverified: low confidence
                </span>
              )}
              {c.rationale && <span>{c.rationale}</span>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

export function MaskedContacts({ contacts }: { contacts: { email: string; phone: string; masked: boolean } }) {
  return (
    <div className="space-y-0.5 text-sm">
      <p className="flex items-center gap-1.5">
        {contacts.masked && <Lock className="size-3.5 text-muted-foreground" aria-hidden />}
        <span className="tabular-nums">{contacts.email}</span>
      </p>
      <p className="tabular-nums">{contacts.phone}</p>
      {contacts.masked && <p className="text-xs text-muted-foreground">Contact details unlock when you reach the interview stage.</p>}
    </div>
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
