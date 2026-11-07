import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { EvidenceList, MaskedContacts, ScoreBadge, StageBadge } from '@/components/score'
import { Async, Skeleton } from '@/components/states'
import { Button } from '@/components/ui/button'
import { notice, years } from '@/lib/format'
import { usePortalCandidate } from '@/lib/queries'
import { DecisionActions, DecisionStatus } from './Actions'
import { HowWeScreen } from './HowWeScreen'

export function PortalCandidatePage() {
  const { id = '' } = useParams()
  const query = usePortalCandidate(id)
  const [how, setHow] = useState(false)
  return (
    <AppShell narrow>
      <Link to="/portal" className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-3.5" aria-hidden /> Your shortlist
      </Link>
      <Async query={query} skeleton={<div className="space-y-3"><Skeleton className="h-16 w-full" /><Skeleton className="h-64 w-full" /></div>}>
        {(c) => (
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h1>{c.full_name}</h1>
                  <p className="text-muted-foreground">{c.current_role} · {c.requisition.title}</p>
                </div>
                <ScoreBadge score={c.score} size="lg" />
              </div>
              <p className="text-small text-muted-foreground">
                {years(c.experience_years)} · notice {notice(c.notice_days)}{c.location && ` · ${c.location}`} <StageBadge stage={c.stage} />
              </p>
              {c.recruiter_note && <p className="rounded-input bg-surface-1 p-3 text-small"><span className="text-small text-muted-foreground">From your recruiter</span><br />{c.recruiter_note}</p>}
              <MaskedContacts contacts={c.contacts} />
            </div>
            <DecisionStatus card={c} />
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="">Why this score</h2>
                <Button variant="ghost" size="sm" onClick={() => setHow(true)}>How we screen</Button>
              </div>
              {c.score.state === 'scored' ? (
                <EvidenceList criteria={c.score.criteria} />
              ) : (
                <p className="rounded-xl border border-dashed p-3 text-small text-muted-foreground">
                  This CV could not be scored automatically, so our recruiter reviewed it by hand.
                </p>
              )}
            </section>
            <section className="space-y-2">
              <h2>CV</h2>
              <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words rounded-card border bg-surface-1 p-5 font-sans text-small leading-relaxed">{c.cv_text}</pre>
              {c.contacts.masked && <p className="text-small text-muted-foreground">Emails, phone numbers and profile links in the CV are hidden until the interview stage.</p>}
            </section>
            <div className="sticky bottom-0 -mx-4 border-t bg-ws p-4">
              <DecisionActions card={c} />
            </div>
            <HowWeScreen open={how} onClose={() => setHow(false)} />
          </div>
        )}
      </Async>
    </AppShell>
  )
}
