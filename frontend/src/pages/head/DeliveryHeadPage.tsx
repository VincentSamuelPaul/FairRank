import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { AppShell, PageHeader } from '@/components/AppShell'
import { BandPill } from '@/components/score'
import { Async, EmptyState } from '@/components/states'
import { Select } from '@/components/ui/field'
import { STAGES } from '@/lib/format'
import { useAgreement, usePipelineSummary } from '@/lib/queries'
import { cn } from '@/lib/utils'

function SubNav() {
  const cls = ({ isActive }: { isActive: boolean }) =>
    cn('-mb-px border-b-2 px-3 py-2 text-sm', isActive ? 'border-primary font-medium' : 'border-transparent text-muted-foreground hover:text-foreground')
  return (
    <nav aria-label="Delivery sections" className="mb-6 flex gap-1 border-b">
      <NavLink to="/pipeline" end className={cls}>Pipeline by requisition</NavLink>
      <NavLink to="/pipeline/report" className={cls}>AI vs recruiter</NavLink>
    </nav>
  )
}

export function PipelineOverviewPage() {
  const query = usePipelineSummary()
  return (
    <AppShell>
      <PageHeader title="Delivery" subtitle="Where every requisition stands, from sourced to joined." />
      <SubNav />
      <Async query={query} isEmpty={(d) => d.length === 0} empty={<EmptyState title="No requisitions yet" />}>
        {(rows) => (
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full min-w-[44rem] text-sm">
              <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">Requisition</th>
                  {STAGES.map((s) => <th key={s.key} scope="col" className="px-2 py-2 text-right font-medium">{s.label}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r) => (
                  <tr key={r.id} className="hover:bg-accent/30">
                    <th scope="row" className="px-3 py-3 text-left font-normal">
                      <Link to={`/requisitions/${r.id}/pipeline`} className="font-medium hover:underline">{r.title}</Link>
                      <span className="block text-xs text-muted-foreground">{r.client} · {r.total} CVs</span>
                    </th>
                    {STAGES.map((s) => (
                      <td key={s.key} className={cn('px-2 py-3 text-right tabular-nums', r.counts[s.key] === 0 && 'text-muted-foreground/50')}>{r.counts[s.key]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Async>
    </AppShell>
  )
}

export function AgreementReportPage() {
  const [days, setDays] = useState(7)
  const query = useAgreement(days)
  return (
    <AppShell>
      <PageHeader
        title="AI vs recruiter"
        subtitle="Do recruiters pick the candidates the AI ranks highest? A sample for you to review, not a verdict on either."
        actions={
          <Select aria-label="Time window" className="w-40" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </Select>
        }
      />
      <SubNav />
      <Async query={query} isEmpty={(d) => d.requisitions.length === 0} empty={<EmptyState title="No submissions in this window">When recruiters submit candidates, this report compares their picks with the AI’s top ranks.</EmptyState>}>
        {(r) => (
          <div className="space-y-8">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border p-4">
                <p className="text-sm text-muted-foreground">Recruiter picks in the AI’s top ranks</p>
                <p className="mt-1 text-4xl font-semibold tabular-nums tracking-tight">{r.overall.agreement_pct === null ? '—' : `${r.overall.agreement_pct}%`}</p>
              </div>
              <div className="rounded-xl border p-4">
                <p className="text-sm text-muted-foreground">Candidates submitted</p>
                <p className="mt-1 text-4xl font-semibold tabular-nums tracking-tight">{r.overall.submitted}</p>
              </div>
              <div className="rounded-xl border p-4">
                <p className="text-sm text-muted-foreground">Requisitions</p>
                <p className="mt-1 text-4xl font-semibold tabular-nums tracking-tight">{r.overall.requisitions}</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              For each requisition, N is the number of candidates a recruiter submitted. Agreement is how many of them sit in the AI’s top N. A disagreement is a prompt to look, because the recruiter may know something the CV does not.
            </p>

            <section className="space-y-3">
              <h2 className="font-medium">By requisition</h2>
              <ul className="space-y-3">
                {r.requisitions.map((q) => (
                  <li key={q.requisition_id} className="space-y-3 rounded-xl border p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <Link to={`/requisitions/${q.requisition_id}`} className="font-medium hover:underline">{q.title}</Link>
                      <span className="text-sm text-muted-foreground">
                        {q.in_ai_top_n} of {q.submitted} in AI top {q.submitted} · <strong className="text-foreground">{q.agreement_pct}%</strong>
                      </span>
                    </div>
                    {q.disagreements.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Recruiter and AI picks match.</p>
                    ) : (
                      <ul className="divide-y text-sm">
                        {q.disagreements.map((d) => (
                          <li key={d.type + d.candidate_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                            <span>
                              <Link to={`/candidates/${d.candidate_id}`} className="hover:underline">{d.name}</Link>
                              <span className="ml-2 text-muted-foreground">
                                {d.type === 'recruiter_chose_lower_ranked' ? 'Submitted, but ranked lower by the AI' : 'High AI rank, not submitted'}
                              </span>
                            </span>
                            <span className="flex items-center gap-2 text-muted-foreground">
                              {d.ai_rank ? `AI rank #${d.ai_rank}` : 'Not scored'}
                              {d.score !== null && <span className="tabular-nums text-foreground">{Math.round(d.score)}</span>}
                              {d.band && <BandPill band={d.band} />}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="font-medium">What clients did with each band</h2>
              <div className="overflow-x-auto rounded-xl border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
                    <tr><th className="px-3 py-2 font-medium">AI band</th><th className="px-3 py-2 text-right font-medium">Submitted</th><th className="px-3 py-2 text-right font-medium">Accepted</th><th className="px-3 py-2 text-right font-medium">Rejected</th><th className="px-3 py-2 text-right font-medium">Awaiting</th></tr>
                  </thead>
                  <tbody className="divide-y">
                    {r.acceptance_by_band.map((b) => (
                      <tr key={b.band}>
                        <td className="px-3 py-2 capitalize">{b.band === 'unscored' ? 'Not scored' : b.band}</td>
                        {[b.submitted, b.accepted, b.rejected, b.pending].map((n, i) => <td key={i} className="px-3 py-2 text-right tabular-nums">{n}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-muted-foreground">A weekly job also emails (mock) this summary to the delivery head.</p>
            </section>
          </div>
        )}
      </Async>
    </AppShell>
  )
}
