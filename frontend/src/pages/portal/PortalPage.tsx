import { Info } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { MaskedContacts, ScoreBadge, StageBadge } from '@/components/score'
import { Async, EmptyState, ListSkeleton } from '@/components/states'
import { EvidenceQuote } from '@/components/ui/evidence-quote'
import { notice, years } from '@/lib/format'
import { usePortalCandidates, usePortalRequisitions } from '@/lib/queries'
import type { ClientCard } from '@/lib/types'
import { cn } from '@/lib/utils'
import { DecisionActions, DecisionStatus } from './Actions'
import { HowWeScreen } from './HowWeScreen'

/** The two strongest verified quotes: the reasons this candidate is on your list. */
function topEvidence(card: ClientCard) {
  return [...card.score.criteria].filter((c) => c.evidence_status === 'verified').sort((a, b) => b.points - a.points).slice(0, 2)
}

function Card({ card }: { card: ClientCard }) {
  const ev = topEvidence(card)
  return (
    <li className="space-y-4 rounded-card border bg-surface-1 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link to={`/portal/candidates/${card.id}`} className="block truncate text-h2 hover:underline">{card.full_name}</Link>
          <p className="text-small text-text-2">{card.current_role}</p>
          <p className="tnum text-small text-text-2">
            {years(card.experience_years)} · notice {notice(card.notice_days)}{card.location && ` · ${card.location}`}
          </p>
        </div>
        <ScoreBadge score={card.score} stacked />
      </div>
      {ev.map((c) => (
        <EvidenceQuote key={c.criterion_id} criterion={c.name} quote={c.quote} status="verified" unverified={c.unverified} clamp={2} />
      ))}
      <MaskedContacts contacts={card.contacts} />
      <DecisionStatus card={card} />
      <DecisionActions card={card} />
      <div className="flex min-h-11 items-center justify-between gap-3 border-t pt-3">
        <StageBadge stage={card.stage} />
        <Link to={`/portal/candidates/${card.id}`} className="inline-flex min-h-11 items-center text-small underline underline-offset-4">Full evidence and CV</Link>
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
    <AppShell narrow>
      <div className="mb-5 space-y-2">
        <h1>Your shortlist</h1>
        <p className="text-small text-text-2">Candidates our recruiters reviewed and submitted for your roles, best match first.</p>
        <button type="button" onClick={() => setHow(true)} className="inline-flex min-h-11 items-center gap-1.5 text-small underline underline-offset-4">
          <Info className="size-4" aria-hidden /> How we screen
        </button>
      </div>
      {(reqs.data?.length ?? 0) > 1 && (
        <div role="group" aria-label="Filter by role" className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {[{ id: undefined, title: 'All roles', awaiting_decision: reqs.data!.reduce((s, r) => s + r.awaiting_decision, 0) }, ...reqs.data!].map((r) => (
            <button
              key={r.id ?? 'all'}
              type="button"
              aria-pressed={reqId === r.id}
              onClick={() => setReqId(r.id)}
              className={cn('inline-flex h-11 shrink-0 items-center rounded-pill border px-4 text-small', reqId === r.id ? 'border-accent bg-accent text-on-accent' : 'border-border-strong')}
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
