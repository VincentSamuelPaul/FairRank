import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AppShell, PageHeader } from '@/components/AppShell'
import { Async, EmptyState } from '@/components/states'
import { Button } from '@/components/ui/button'
import { DistBar } from '@/components/ui/dist-bar'
import { Monogram } from '@/components/ui/monogram'
import { PipelineProgress } from '@/components/ui/pipeline-progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useMe } from '@/lib/auth'
import { dateOnly, notice, STAGES, years } from '@/lib/format'
import { CountUp } from '@/lib/motion'
import { useAllRanked, useRequisitions } from '@/lib/queries'
import type { RankedList, Requisition, Stage } from '@/lib/types'
import { NewRequisition } from './NewRequisition'

const FLOW = STAGES.filter((s) => s.key !== 'rejected').map((s) => s.key)

/** Everything on a card is derived from the ranked list the API already serves. */
function summarise(list?: RankedList) {
  const cands = list?.candidates ?? []
  const reached = cands.filter((c) => c.stage !== 'rejected').map((c) => FLOW.indexOf(c.stage))
  return {
    furthest: reached.length ? (FLOW[Math.max(...reached)] as Stage) : null,
    unread: cands.filter((c) => c.score.state === 'scored' && !c.viewed && c.stage !== 'rejected').length,
    dist: { strong: list?.counts.strong ?? 0, possible: list?.counts.possible ?? 0, weak: list?.counts.weak ?? 0, review: (list?.counts.needs_review ?? 0) + (list?.counts.failed ?? 0) },
  }
}

function Card({ r, list, i }: { r: Requisition; list?: RankedList; i: number }) {
  const s = summarise(list)
  return (
    <li className="rise-in" style={{ '--d': `${i * 40}ms` } as React.CSSProperties}>
      <Link to={`/requisitions/${r.id}`} className="surface-card group block h-full space-y-4 rounded-card border p-5 transition-[transform,border-color] duration-(--dur-fast) ease-ui hover:-translate-y-0.5 hover:border-border-strong">
        <div className="flex items-start gap-3">
          <Monogram name={r.client.name} />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-body font-medium">{r.title}</h2>
            <p className="truncate text-small text-text-2">{r.client.name}{r.location && ` · ${r.location}`}</p>
          </div>
          {s.unread > 0 && (
            <span className="inline-flex shrink-0 items-center gap-1.5 text-micro uppercase text-signal" title={`${s.unread} scored CVs nobody has opened yet`}>
              <span aria-hidden className="size-1.5 rounded-pill bg-signal" />
              <span className="tnum">{s.unread}</span> unread
            </span>
          )}
        </div>
        <p className="tnum text-small text-text-2">
          {r.exp_min_years !== null && `${years(r.exp_min_years)}–${years(r.exp_max_years)}`}
          {r.notice_max_days !== null && ` · notice ≤ ${notice(r.notice_max_days)}`}
          {r.scorecard_version && ` · scorecard v${r.scorecard_version}`}
        </p>
        {(r.counts?.candidates ?? 0) === 0 ? (
          <p className="rounded-input border border-dashed px-3 py-3 text-small text-text-2">No CVs yet. Upload a batch to see who to read first.</p>
        ) : (
          <>
            <DistBar counts={s.dist} />
            <PipelineProgress furthest={s.furthest} />
          </>
        )}
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t pt-3 text-small">
          <span><strong className="tnum font-medium">{r.counts?.candidates ?? 0}</strong> <span className="text-text-2">{r.counts?.candidates === 1 ? 'CV' : 'CVs'}</span></span>
          <span><strong className="tnum font-medium">{r.counts?.submitted ?? 0}</strong> <span className="text-text-2">submitted</span></span>
          <span className="tnum ml-auto text-text-2">{dateOnly(r.created_at)}</span>
        </div>
      </Link>
    </li>
  )
}

function CardSkeleton() {
  return (
    <li className="surface-card space-y-4 rounded-card border p-5" aria-hidden>
      <div className="flex gap-3"><Skeleton className="size-10" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-2/3" /><Skeleton className="h-3 w-1/2" /></div></div>
      <Skeleton className="h-3 w-3/4" />
      <div className="space-y-2"><Skeleton className="h-1.5 w-full" /><Skeleton className="h-3 w-2/3" /></div>
      <div className="space-y-2"><Skeleton className="h-1.5 w-full" /><Skeleton className="h-3 w-1/3" /></div>
      <Skeleton className="h-4 w-full" />
    </li>
  )
}

function Stat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="surface-card rounded-card border px-4 py-3.5 sm:px-5">
      <p className="text-micro uppercase text-text-2">{label}</p>
      <p className="tnum text-h1">{value === null ? '–' : <CountUp value={value} />}</p>
    </div>
  )
}

export function RequisitionsPage() {
  const { data: user } = useMe()
  const query = useRequisitions()
  const reqs = query.data ?? []
  const ranked = useAllRanked(reqs.map((r) => r.id))
  const [open, setOpen] = useState(false)
  const [params, setParams] = useSearchParams()
  const canEdit = user?.role === 'recruiter'
  useEffect(() => {
    if (params.get('new') === '1' && canEdit) {
      setOpen(true)
      setParams({}, { replace: true })
    }
  }, [params, canEdit, setParams])

  const loaded = ranked.length > 0 && ranked.every((q) => q.data)
  const all = ranked.flatMap((q) => q.data?.candidates ?? [])
  const weekAgo = Date.now() - 7 * 864e5
  const stats = {
    open: reqs.filter((r) => r.status === 'open').length,
    screened: all.filter((c) => c.score.state === 'scored' && new Date(c.created_at).getTime() >= weekAgo).length,
    awaiting: all.filter((c) => c.stage === 'submitted').length,
  }
  return (
    <AppShell>
      <PageHeader
        title="Requisitions"
        subtitle="Upload CVs against a job and see the best first, with reasons."
        actions={canEdit && <Button onClick={() => setOpen(true)}><Plus /> New requisition</Button>}
      />
      {query.data && reqs.length > 0 && (
        <div className="mb-6 grid grid-cols-3 gap-2 sm:gap-3">
          <Stat label="Open requisitions" value={stats.open} />
          <Stat label="CVs screened this week" value={loaded ? stats.screened : null} />
          <Stat label="Awaiting client" value={loaded ? stats.awaiting : null} />
        </div>
      )}
      <Async
        query={query}
        skeleton={<ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">{[0, 1, 2, 3].map((n) => <CardSkeleton key={n} />)}</ul>}
        isEmpty={(d) => d.length === 0}
        empty={
          <EmptyState title="No requisitions yet" action={canEdit && <Button onClick={() => setOpen(true)}>Paste a JD</Button>}>
            Paste a job description to get a scorecard, then upload CVs.
          </EmptyState>
        }
      >
        {(list) => (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {list.map((r, i) => <Card key={r.id} r={r} list={ranked[i]?.data} i={i} />)}
          </ul>
        )}
      </Async>
      <NewRequisition open={open} onClose={() => setOpen(false)} />
    </AppShell>
  )
}
