import { Info, Quote } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { MaskedContacts, ScoreBadge, StageBadge } from '@/components/score'
import { Async, EmptyState, ListSkeleton } from '@/components/states'
import { Button } from '@/components/ui/button'
import { notice, years } from '@/lib/format'
import { usePortalCandidates, usePortalRequisitions } from '@/lib/queries'
import type { ClientCard } from '@/lib/types'
import { cn } from '@/lib/utils'
import { DecisionActions, DecisionStatus } from './Actions'
import { HowWeScreen } from './HowWeScreen'

/** The strongest verified quote: the reason this candidate is on your list. */
function topEvidence(card: ClientCard) {
  return [...card.score.criteria].filter((c) => c.evidence_status === 'verified').sort((a, b) => b.points - a.points)[0]
}

function Card({ card }: { card: ClientCard }) {
  const ev = topEvidence(card)
  return (
    <li className="space-y-3 rounded-card border bg-surface-1 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link to={`/portal/candidates/${card.id}`} className="block truncate text-lg font-semibold leading-tight hover:underline">{card.full_name}</Link>
          <p className="text-sm text-muted-foreground">{card.current_role}</p>
        </div>
        <ScoreBadge score={card.score} />
      </div>
      <p className="text-sm text-muted-foreground">
        {years(card.experience_years)} · notice {notice(card.notice_days)}{card.location && ` · ${card.location}`}
      </p>
      {ev && (
        <blockquote className="flex gap-2 border-l-2 border-primary/50 pl-3 text-sm">
          <Quote className="mt-0.5 size-3.5 shrink-0 text-primary" aria-hidden />
          <span>
            <span className="block text-xs text-muted-foreground">{ev.name}</span>“{ev.quote}”
          </span>
        </blockquote>
      )}
      <MaskedContacts contacts={card.contacts} />
      <DecisionStatus card={card} />
      <DecisionActions card={card} compact />
      <div className="flex items-center justify-between pt-1 text-sm">
        <StageBadge stage={card.stage} />
        <Link to={`/portal/candidates/${card.id}`} className="text-primary hover:underline">Full evidence and CV</Link>
      </div>
    </li>
  )
}

export function PortalPage() {
  const reqs = usePortalRequisitions()
  const [reqId, setReqId] = useState<string | undefined>()
  const [how, setHow] = useState(false)
  const query = usePortalCandidates(reqId)
  return (
    <AppShell narrow extra={<Button variant="ghost" size="sm" onClick={() => setHow(true)}><Info /> <span className="hidden sm:inline">How we screen</span><span className="sm:hidden">How</span></Button>}>
      <div className="mb-5 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Your shortlist</h1>
        <p className="text-sm text-muted-foreground">Candidates our recruiters reviewed and submitted for your roles, best match first.</p>
      </div>
      {(reqs.data?.length ?? 0) > 1 && (
        <div role="group" aria-label="Filter by role" className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {[{ id: undefined, title: 'All roles', awaiting_decision: reqs.data!.reduce((s, r) => s + r.awaiting_decision, 0) }, ...reqs.data!].map((r) => (
            <button
              key={r.id ?? 'all'}
              type="button"
              aria-pressed={reqId === r.id}
              onClick={() => setReqId(r.id)}
              className={cn('shrink-0 rounded-full px-3.5 py-2 text-sm ring-1', reqId === r.id ? 'bg-primary text-primary-foreground ring-primary' : 'ring-foreground/15')}
            >
              {r.title}
              {r.awaiting_decision > 0 && <span className="ml-1.5 tabular-nums opacity-80">{r.awaiting_decision}</span>}
            </button>
          ))}
        </div>
      )}
      <Async
        query={query}
        skeleton={<ListSkeleton rows={3} />}
        isEmpty={(d) => d.length === 0}
        empty={<EmptyState title="Nothing to review yet">When your recruiter submits candidates for your roles, they appear here.</EmptyState>}
      >
        {(cards) => (
          <ul className="space-y-4">
            {cards.map((c) => <Card key={c.id} card={c} />)}
          </ul>
        )}
      </Async>
      <HowWeScreen open={how} onClose={() => setHow(false)} />
    </AppShell>
  )
}
