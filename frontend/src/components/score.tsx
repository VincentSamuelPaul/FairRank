import { Lock } from 'lucide-react'
import type { Band, ScorePayload, Stage } from '@/lib/types'
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
