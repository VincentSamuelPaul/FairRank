import { ChevronDown, Copy, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Async, EmptyState, ListSkeleton } from '@/components/states'
import { CriterionChips, EvidenceList, RetryHint, ScoreBadge, StageBadge } from '@/components/score'
import { Button, buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/field'
import { useMe } from '@/lib/auth'
import { notice, STAGES, years } from '@/lib/format'
import { useRanked, useRetryScoring } from '@/lib/queries'
import type { CandidateRow } from '@/lib/types'
import { cn } from '@/lib/utils'

const BANDS = [
  { key: '', label: 'All', count: 'total' },
  { key: 'strong', label: 'Strong', count: 'strong' },
  { key: 'possible', label: 'Possible', count: 'possible' },
  { key: 'weak', label: 'Weak', count: 'weak' },
  { key: 'unscored', label: 'Not scored', count: 'unscored' },
] as const

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

function NextAction({ row }: { row: CandidateRow }) {
  const retry = useRetryScoring()
  const a = row.next_action
  if (a.code === 'open' || a.code === 'submit')
    return (
      <Link to={`/candidates/${row.id}`} className={buttonVariants({ variant: a.code === 'submit' ? 'default' : 'outline', size: 'sm' })}>
        {a.label}
      </Link>
    )
  if (a.code === 'retry')
    return (
      <Button variant="outline" size="sm" disabled={retry.isPending || retry.isSuccess} onClick={() => retry.mutate(row.id)}>
        {retry.isSuccess ? 'Queued' : a.label}
      </Button>
    )
  if (a.code === 'fix_file')
    return (
      <Link to="upload" className={buttonVariants({ variant: 'outline', size: 'sm' })}>
        {a.label}
      </Link>
    )
  return <span className="text-sm text-muted-foreground">{a.label}</span>
}

function Row({ row, rank }: { row: CandidateRow; rank: number | null }) {
  const [open, setOpen] = useState(false)
  const hasEvidence = row.score.criteria.length > 0
  return (
    <li className="rounded-xl border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="w-6 text-sm tabular-nums text-muted-foreground">{rank ? `#${rank}` : '–'}</span>
            <Link to={`/candidates/${row.id}`} className="font-medium hover:underline">
              {row.full_name || row.original_name || 'Unnamed CV'}
            </Link>
            <StageBadge stage={row.stage} />
            {row.external_id && <span className="text-xs text-muted-foreground">{row.external_id}</span>}
            {row.duplicate_of && (
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs" title={row.cv_note}>
                <Copy className="size-3" aria-hidden />
                Possible duplicate of {row.duplicate_of.external_id || row.duplicate_of.full_name || 'another record'}
              </span>
            )}
          </div>
          <p className="pl-8 text-sm text-muted-foreground">
            {[row.current_role, years(row.experience_years), `notice ${notice(row.notice_days)}`, row.location].filter(Boolean).join(' · ')}
          </p>
          {hasEvidence && (
            <div className="pl-8">
              <CriterionChips criteria={row.score.criteria} />
              {row.score.missing_must_haves.length > 0 && (
                <p className="mt-1.5 text-xs text-muted-foreground">No evidence found for: {row.score.missing_must_haves.join(', ')}</p>
              )}
            </div>
          )}
          {row.score.state === 'needs_manual_review' && (
            <p className="pl-8 text-sm text-muted-foreground">No readable text (scanned or image-only). Open the file and review it by hand.</p>
          )}
          <div className="pl-8">
            <RetryHint row={row} />
            {row.score.state === 'cv_failed' && <p className="text-sm text-destructive">{row.cv_note || row.score.error}</p>}
          </div>
        </div>
        <div className="flex shrink-0 items-center justify-between gap-3 pl-8 sm:w-44 sm:flex-col sm:items-end sm:pl-0">
          <ScoreBadge score={row.score} />
          <NextAction row={row} />
        </div>
      </div>
      {hasEvidence && (
        <div className="mt-3 pl-8">
          <button
            type="button"
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            <ChevronDown className={cn('size-3.5 transition-transform', open && 'rotate-180')} aria-hidden />
            {open ? 'Hide evidence' : 'Show evidence'}
          </button>
          {open && (
            <div className="mt-3">
              <EvidenceList criteria={row.score.criteria} />
            </div>
          )}
        </div>
      )}
    </li>
  )
}

export function RankedPage() {
  const { id = '' } = useParams()
  const { data: user } = useMe()
  const [q, setQ] = useState('')
  const [band, setBand] = useState('')
  const [flag, setFlag] = useState('')
  const [stage, setStage] = useState('')
  const dq = useDebounced(q)
  const query = useRanked(id, { q: dq || undefined, band: band || undefined, flag: flag || undefined, stage: stage || undefined })
  const filtered = !!(dq || band || flag || stage)

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <div className="relative md:max-w-sm md:flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input aria-label="Search candidates" className="h-9 pl-8 md:h-8" placeholder="Search name, skill or anything in the CV" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <Select aria-label="Filter by flag" className="md:w-44" value={flag} onChange={(e) => setFlag(e.target.value)}>
            <option value="">All CVs</option>
            <option value="needs_attention">Needs attention</option>
            <option value="duplicates">Possible duplicates</option>
          </Select>
          <Select aria-label="Filter by stage" className="md:w-40" value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="">Any stage</option>
            {STAGES.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div role="group" aria-label="Filter by band" className="flex flex-wrap gap-2">
        {BANDS.map((b) => (
          <button
            key={b.key}
            type="button"
            aria-pressed={band === b.key}
            onClick={() => setBand(b.key)}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm ring-1 transition-colors',
              band === b.key ? 'bg-primary text-primary-foreground ring-primary' : 'bg-background ring-foreground/15 hover:bg-muted',
            )}
          >
            {b.label}
            <span className="tabular-nums opacity-80">{query.data?.counts[b.count] ?? '–'}</span>
          </button>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Scores guide your order of reading. Nobody is rejected or hidden by a score: low scorers stay here and stay searchable.
      </p>

      <Async
        query={query}
        skeleton={<ListSkeleton rows={5} />}
        isEmpty={(d) => d.candidates.length === 0}
        empty={
          filtered ? (
            <EmptyState title="No CVs match these filters" action={<Button variant="outline" onClick={() => { setQ(''); setBand(''); setFlag(''); setStage('') }}>Clear filters</Button>} />
          ) : (
            <EmptyState
              title="No CVs yet"
              action={user?.role === 'recruiter' && <Link to="upload" className={buttonVariants()}>Upload CVs</Link>}
            >
              Upload a batch of PDF or DOCX CVs. They are parsed and scored, best first, with the evidence quoted from each CV.
            </EmptyState>
          )
        }
      >
        {(data) => {
          // rank counts scored CVs only; the rest are listed after them, unranked
          const ranks = data.candidates.reduce<(number | null)[]>((acc, c) => {
            const done = acc.filter((r) => r !== null).length
            acc.push(c.score.state === 'scored' ? done + 1 : null)
            return acc
          }, [])
          return (
            <ul className="space-y-3">
              {data.candidates.map((c, i) => (
                <Row key={c.id} row={c} rank={ranks[i]} />
              ))}
            </ul>
          )
        }}
      </Async>
    </div>
  )
}
