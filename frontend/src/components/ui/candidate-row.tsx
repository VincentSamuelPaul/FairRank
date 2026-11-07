import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { CandidateRow as Row, CriterionScore } from '@/lib/types'
import { notice, years } from '@/lib/format'
import { Button, buttonVariants } from '@/components/ui/button'
import { CriterionDots } from '@/components/ui/criterion-dots'
import { EvidenceChip } from '@/components/ui/evidence-chip'
import { ScoreRing } from '@/components/ui/score-ring'
import { StageChip, StatusChip } from '@/components/ui/status-chip'

export interface RowActions {
  /** Recruiters can submit; the delivery head only reads. */
  canAct: boolean
  onSubmit: () => void
  onRetry: () => void
  busy?: boolean
}

/** Left edge of a row: solid in the band colour; dashed for Needs review (no score to colour by). */
function stripe(row: Row): string {
  if (row.score.state === 'needs_manual_review') return 'bg-[repeating-linear-gradient(180deg,var(--info)_0_6px,transparent_6px_10px)]'
  const b = row.score.band
  return b === 'strong' ? 'bg-ok' : b === 'possible' ? 'bg-warn' : b === 'weak' ? 'bg-bad' : 'bg-border-strong'
}

const NOT_OPENED = 'Open the CV first. You can submit a candidate once you have read their CV.'

/** The single recommended next action is the only cream pill; everything else is ghost. "Open CV" comes first; Submit is enabled only after the CV was opened. */
function Actions({ row, a, uploadTo }: { row: Row; a: RowActions; uploadTo: string }) {
  const code = row.next_action.code
  const open = `/candidates/${row.id}`
  const openBtn = (primary: boolean) => (
    <Link to={open} className={buttonVariants({ variant: primary ? 'primary' : 'ghost', className: 'group/button w-full max-md:min-h-11 md:w-auto' })}>
      Open CV
      <ArrowRight className="size-4 transition-transform duration-(--dur-fast) ease-ui group-hover/button:translate-x-0.5" aria-hidden />
    </Link>
  )
  const col = 'flex w-full flex-col gap-1.5 md:w-auto md:items-end'
  if (code === 'wait') return <p className="text-small text-text-2">{row.next_action.label}</p>
  if (code === 'fix_file') return <div className={col}><Link to={uploadTo} className={buttonVariants({ className: 'w-full max-md:min-h-11 md:w-auto' })}>{row.next_action.label}</Link></div>
  if (code === 'retry')
    return (
      <div className={col}>
        <Button className="w-full max-md:min-h-11 md:w-auto" disabled={a.busy} loading={a.busy} onClick={a.onRetry}>{a.busy ? 'Queued' : row.next_action.label}</Button>
        {openBtn(false)}
      </div>
    )
  if (code === 'submit' && a.canAct)
    return (
      <div className={col}>
        <Button arrow className="w-full max-md:min-h-11 md:w-auto" loading={a.busy} disabled={a.busy} onClick={a.onSubmit}>{a.busy ? 'Submitting' : 'Submit to client'}</Button>
        {openBtn(false)}
      </div>
    )
  if (code === 'open' && a.canAct && !row.submitted)
    return (
      <div className={col}>
        {openBtn(true)}
        <Button variant="ghost" size="sm" disabled disabledReason={NOT_OPENED} className="w-full max-md:min-h-11 md:w-auto">Submit to client</Button>
      </div>
    )
  return <div className={col}>{openBtn(code === 'open')}</div>
}

const norm = (t: string) => t.toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim()
/** Strongest verified quotes, skipping near-identical ones (e.g. the same job title shown twice). */
function distinctTop(criteria: CriterionScore[], n = 2): CriterionScore[] {
  const out: CriterionScore[] = []
  for (const c of [...criteria].filter((x) => x.evidence_status === 'verified').sort((a, b) => b.points - a.points)) {
    const q = norm(c.quote)
    if (out.some((o) => { const p = norm(o.quote); return p === q || p.includes(q) || q.includes(p) })) continue
    out.push(c)
    if (out.length === n) break
  }
  return out
}

/** Left: rank (large, dim) + ScoreRing. Middle: name, one-line meta, two evidence chips, evidence dots. Right: one next action. Weak and unscored rows look exactly as important as strong ones. */
export function CandidateRow({ row, rank, actions, uploadTo = 'upload' }: { row: Row; rank: number | null; actions: RowActions; uploadTo?: string }) {
  const name = row.full_name || row.original_name || 'Unnamed CV'
  const top = distinctTop(row.score.criteria)
  const meta = [row.current_role, years(row.experience_years), `notice ${notice(row.notice_days)}`, row.location].filter(Boolean).join(' · ')
  const scored = row.score.state === 'scored'
  return (
    <li className="surface-card relative grid grid-cols-1 gap-y-3 overflow-hidden rounded-card border p-4 pl-5 md:grid-cols-[7rem_1fr_11rem] md:gap-x-6 md:p-5 md:pl-6">
      <span aria-hidden className={cn('absolute inset-y-0 left-0 w-(--stripe)', stripe(row))} />
      <div className="flex items-center gap-3 md:flex-col md:gap-1.5 md:row-span-2">
        <span className="tnum text-h1 text-text-3" aria-label={rank ? `Rank ${rank}` : 'Not ranked'}>{rank ?? '–'}</span>
        <ScoreRing value={row.score.total} band={row.score.band} state={row.score.state} stackedMd glow />
      </div>

      <div className="min-w-0 space-y-1 md:col-start-2">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <Link to={`/candidates/${row.id}`} className="inline-flex max-md:min-h-11 items-center truncate text-h2 hover:underline md:text-h1">{name}</Link>
          <StageChip stage={row.stage} />
          {row.duplicate_of && <StatusChip tone="warn">Duplicate</StatusChip>}
          {row.score.state === 'needs_manual_review' && <StatusChip tone="info">Needs review</StatusChip>}
          {row.score.state === 'failed' && <StatusChip tone="bad">Scoring failed</StatusChip>}
        </div>
        <p className="truncate text-small text-text-2">{meta}</p>
        {row.duplicate_of && <p className="text-small text-text-2">Possible duplicate of {row.duplicate_of.external_id || row.duplicate_of.full_name || 'another record'}.</p>}
      </div>

      <div className="min-w-0 space-y-3 md:col-start-2">
        {top.length > 0 && (
          <div className="grid gap-2 md:grid-cols-2">
            {top.map((c) => <EvidenceChip key={c.criterion_id} criterion={c.name} quote={c.quote} unverified={c.unverified} />)}
          </div>
        )}
        {scored && row.score.criteria.length > 0 && <CriterionDots criteria={row.score.criteria} />}
        {scored && top.length === 0 && <p className="text-small text-text-2">No evidence found for any criterion. Read the CV yourself.</p>}
        {scored && row.score.missing_must_haves.length > 0 && <p className="text-small text-text-2">No evidence found for: {row.score.missing_must_haves.join(', ')}</p>}
        {row.score.state === 'needs_manual_review' && <p className="text-small text-text-2">No readable text (scanned or image-only). Open the file and review it by hand. It is not rejected or hidden.</p>}
        {row.score.state === 'failed' && <p className="text-small text-text-2">{row.score.error || 'The AI could not score this CV.'} The CV is still here to read.</p>}
        {row.score.state === 'cv_failed' && <p className="text-small text-bad">{row.cv_note || row.score.error}</p>}
      </div>

      <div className="flex md:col-start-3 md:row-span-2 md:row-start-1 md:justify-end">
        <Actions row={row} a={actions} uploadTo={uploadTo} />
      </div>
    </li>
  )
}
