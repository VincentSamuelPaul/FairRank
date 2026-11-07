import { Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Async, EmptyState } from '@/components/states'
import { BandBar, type BandKey } from '@/components/ui/band-bar'
import { Button, buttonVariants } from '@/components/ui/button'
import { StickyBar } from '@/components/ui/sticky-bar'
import { CandidateRow } from '@/components/ui/candidate-row'
import { Listbox } from '@/components/ui/listbox'
import { Input } from '@/components/ui/input'
import { RowListSkeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { useMe } from '@/lib/auth'
import { STAGES } from '@/lib/format'
import { CountUp } from '@/lib/motion'
import { useCandidateActions, useRanked, useRequisition } from '@/lib/queries'
import type { CandidateRow as Row } from '@/lib/types'
import { cn } from '@/lib/utils'

type Filter = 'all' | BandKey | 'duplicates'

const toParams = (f: Filter) => ({
  band: f === 'strong' || f === 'possible' || f === 'weak' ? f : undefined,
  flag: f === 'review' ? 'needs_attention' : f === 'duplicates' ? 'duplicates' : undefined,
})

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

function RankedRow({ row, rank, reqId, canAct }: { row: Row; rank: number | null; reqId: string; canAct: boolean }) {
  const { submit, retry } = useCandidateActions(row.id, reqId)
  const { toast } = useToast()
  const fail = (e: Error) => toast(e.message, 'bad')
  return (
    <CandidateRow
      row={row}
      rank={rank}
      actions={{
        canAct,
        busy: submit.isPending || retry.isPending || retry.isSuccess,
        onSubmit: () => submit.mutate('', { onSuccess: () => toast('Submitted to the client with masked contacts', 'ok'), onError: fail }),
        onRetry: () => retry.mutate(undefined, { onSuccess: () => toast('Scoring queued. The list refreshes on its own.', 'info'), onError: fail }),
      }}
    />
  )
}

/** True once the sentinel above the sticky bar has scrolled under the app header. */
function useStuck() {
  const ref = useRef<HTMLDivElement>(null)
  const [stuck, setStuck] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return
    const header = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--header-h')) || 56
    const io = new IntersectionObserver(([e]) => setStuck(!e.isIntersecting), { rootMargin: `-${header}px 0px 0px 0px` })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return { ref, stuck }
}

export function RankedPage() {
  const { id = '' } = useParams()
  const { data: user } = useMe()
  const req = useRequisition(id)
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [stage, setStage] = useState('')
  const dq = useDebounced(q)
  const query = useRanked(id, { q: dq || undefined, stage: stage || undefined, ...toParams(filter) })
  const filtered = !!(dq || stage || filter !== 'all')
  const counts = query.data?.counts
  const { ref: sentinel, stuck } = useStuck()

  return (
    <div className="space-y-5">
      <div ref={sentinel} aria-hidden className="-mb-5 h-px" />
      <div className={cn('md:sticky md:top-(--header-h) md:z-10 -mx-(--gutter) space-y-3 border-b border-transparent bg-ws px-(--gutter) pb-3 pt-3', stuck && 'border-border')}>
        <div className="flex flex-wrap items-baseline justify-between gap-x-4">
          <p className="hidden truncate text-small text-text-2 md:block">{stuck ? <span className="font-medium text-text-1">{req.data?.title}</span> : 'Best match first'}</p>
        </div>
        {counts && <BandBar counts={{ strong: counts.strong, possible: counts.possible, weak: counts.weak, review: counts.needs_review + counts.failed }} value={filter} onChange={setFilter} />}
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <div role="group" aria-label="Other filters" className="flex gap-2 md:flex-1">
            {([['all', 'All', counts?.total], ['duplicates', 'Duplicates', counts?.duplicates]] as const).map(([key, label, n]) => (
              <button
                key={key}
                type="button"
                aria-pressed={filter === key}
                onClick={() => setFilter(key)}
                className={cn(
                  'inline-flex h-11 items-center gap-2 rounded-pill border px-4 text-small transition-colors duration-(--dur-fast) md:h-9',
                  filter === key ? 'border-accent bg-accent text-on-accent' : 'border-border-strong text-text-1 hover:bg-surface-2',
                )}
              >
                {label}
                <span className="tnum opacity-80">{n === undefined ? '–' : <CountUp value={n} />}</span>
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1 md:w-64 md:flex-none">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-text-2" aria-hidden />
              <Input aria-label="Search candidates" className="pl-10" placeholder="Search CVs" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <div className="w-40"><Listbox aria-label="Filter by stage" value={stage} onChange={setStage} options={[{ value: '', label: 'Any stage' }, ...STAGES.map((s) => ({ value: s.key, label: s.label }))]} /></div>
          </div>
        </div>
      </div>

      <p className="text-small text-text-2">Scores guide your order of reading. Nobody is rejected or hidden by a score: Weak and Needs review stay in this list and stay searchable.</p>

      <Async
        query={query}
        skeleton={<RowListSkeleton rows={3} />}
        isEmpty={(d) => d.candidates.length === 0}
        empty={
          filtered ? (
            <EmptyState title="No CVs match these filters" action={<Button variant="secondary" size="sm" onClick={() => { setQ(''); setFilter('all'); setStage('') }}>Clear filters</Button>} />
          ) : (
            <EmptyState title="No CVs yet" action={user?.role === 'recruiter' && <Link to="upload" className={buttonVariants({ size: 'sm' })}>Upload CVs</Link>}>
              Upload a batch of PDF or DOCX CVs. They are parsed and scored, best first, with the evidence quoted from each CV.
            </EmptyState>
          )
        }
      >
        {(data) => {
          // rank counts scored CVs only; the rest are listed after them, unranked
          let n = 0
          const ranks = data.candidates.map((c) => (c.score.state === 'scored' ? ++n : null))
          return (
            <ul className="space-y-3">
              {data.candidates.map((c, i) => (
                <RankedRow key={c.id} row={c} rank={ranks[i]} reqId={id} canAct={user?.role === 'recruiter'} />
              ))}
            </ul>
          )
        }}
      </Async>
      {user?.role === 'recruiter' && (
        <StickyBar from="md">
          <Link to="upload" aria-label="Upload CVs to this requisition" className={buttonVariants({ size: 'lg', className: 'w-full' })}>Upload CVs</Link>
        </StickyBar>
      )}
    </div>
  )
}
