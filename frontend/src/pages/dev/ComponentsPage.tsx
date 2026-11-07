import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { CandidateRow } from '@/components/ui/candidate-row'
import { CriterionList } from '@/components/ui/criterion-row'
import { Dialog } from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { EvidenceQuote } from '@/components/ui/evidence-quote'
import { FairnessPanel } from '@/components/ui/fairness-panel'
import { Field, Select, Textarea } from '@/components/ui/field'
import { GlassPanel } from '@/components/ui/glass-panel'
import { Input } from '@/components/ui/input'
import { PillNav } from '@/components/ui/pill-nav'
import { ScoreRing } from '@/components/ui/score-ring'
import { ListSkeleton, Skeleton } from '@/components/ui/skeleton'
import { StageChip, StatusChip } from '@/components/ui/status-chip'
import { useToast } from '@/components/ui/toast'
import { STAGES } from '@/lib/format'
import type { CandidateRow as Row, CriterionScore, ScoreState } from '@/lib/types'

const crit = (id: number, over: Partial<CriterionScore>): CriterionScore => ({
  criterion_id: id, name: 'Spring Boot', weight: 3, is_must_have: true, points: 90, confidence: 0.9, unverified: false,
  evidence_status: 'verified', quote: 'Built and maintained 12 Spring Boot microservices for payment and order flows', rationale: '', span: [0, 10], ...over,
})
const CRITERIA = [
  crit(1, {}),
  crit(2, { name: 'Java', points: 85, quote: 'Senior Java Developer' }),
  crit(3, { name: 'AWS', is_must_have: false, points: 40, unverified: true, confidence: 0.4, quote: 'Familiar with AWS' }),
  crit(4, { name: 'Kafka', points: 0, evidence_status: 'no_evidence', quote: '' }),
]
const row = (over: Partial<Row> & { state?: ScoreState; total?: number | null; band?: 'strong' | 'possible' | 'weak' | null }): Row => {
  const { state = 'scored', total = 82, band = 'strong', ...rest } = over
  return {
    id: 'x', external_id: 'CND-91022', full_name: 'Candidate 91022', email: '', phone: '', current_role: 'Senior Java Developer', experience_years: 6.5, notice_days: 60,
    location: 'Noida', skills: [], stage: 'screened', cv_status: 'parsed', cv_note: '', original_name: 'cv.pdf', duplicate_of: null,
    score: { state, total, band, criteria: state === 'scored' ? CRITERIA : [], missing_must_haves: state === 'scored' ? ['Kafka'] : [], scorecard_version: 1 },
    viewed: false, submitted: false, next_action: { code: 'open', label: 'Open CV' }, created_at: '', ...rest,
  }
}
const noop = { canAct: true, onSubmit: () => {}, onRetry: () => {} }

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

/** Dev only: every component in every state. Not routed in production builds. */
export function ComponentsPage() {
  const { toast } = useToast()
  const [dlg, setDlg] = useState(false)
  return (
    <div className="mx-auto max-w-5xl space-y-12 px-(--gutter) py-12">
        <header className="space-y-2">
          <h1>Component kit</h1>
          <p className="text-small text-text-2">docs/DESIGN.md section 4. Every component, every state.</p>
        </header>

        <Section title="Button">
          <div className="flex flex-wrap items-center gap-3">
            <Button arrow>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button disabled>Disabled</Button>
            <Button size="sm">Small</Button>
            <Button size="lg" arrow>Large</Button>
          </div>
        </Section>

        <Section title="ScoreRing">
          <div className="flex flex-wrap items-start gap-8">
            <ScoreRing value={82} band="strong" size="lg" />
            <ScoreRing value={63} band="possible" />
            <ScoreRing value={31} band="weak" />
            <ScoreRing value={null} state="needs_manual_review" />
            <ScoreRing value={null} state="failed" />
            <ScoreRing value={null} state="cv_failed" />
            <ScoreRing value={null} state="processing" />
            <ScoreRing value={null} state="no_scorecard" />
            <ScoreRing value={82} band="strong" stacked />
          </div>
        </Section>

        <Section title="StatusChip">
          <div className="flex flex-wrap gap-2">
            {STAGES.map((s) => <StageChip key={s.key} stage={s.key} />)}
            <StatusChip tone="warn">Duplicate</StatusChip>
            <StatusChip tone="info">Needs review</StatusChip>
            <StatusChip tone="bad">Failed</StatusChip>
          </div>
        </Section>

        <Section title="EvidenceQuote">
          <div className="grid gap-4 md:grid-cols-2">
            <EvidenceQuote criterion="Spring Boot" quote={CRITERIA[0].quote} status="verified" />
            <EvidenceQuote criterion="AWS" quote="Familiar with AWS" status="verified" unverified />
            <EvidenceQuote criterion="Kafka" status="no_evidence" />
            <EvidenceQuote criterion="Spring Boot" quote={CRITERIA[0].quote} status="verified" clamp onSelect={() => toast('Scrolled to the match in the CV')} />
          </div>
        </Section>

        <Section title="CriterionRow">
          <CriterionList criteria={CRITERIA} onSelect={() => toast('Scrolled to the match in the CV')} />
        </Section>

        <Section title="CandidateRow">
          <ul className="space-y-3">
            <CandidateRow rank={1} row={row({ id: 'a', viewed: true, next_action: { code: 'submit', label: 'Submit to client' } })} actions={noop} />
            <CandidateRow rank={2} row={row({ id: 'b', total: 63, band: 'possible' })} actions={noop} />
            <CandidateRow rank={3} row={row({ id: 'c', total: 31, band: 'weak' })} actions={noop} />
            <CandidateRow rank={null} row={row({ id: 'd', state: 'needs_manual_review', total: null, band: null })} actions={noop} />
            <CandidateRow rank={null} row={row({ id: 'e', state: 'failed', total: null, band: null, next_action: { code: 'retry', label: 'Retry scoring' } })} actions={noop} />
            <CandidateRow rank={null} row={row({ id: 'f', state: 'processing', total: null, band: null, next_action: { code: 'wait', label: 'Processing…' } })} actions={noop} />
            <CandidateRow rank={4} row={row({ id: 'g', duplicate_of: { id: 'a', external_id: 'CND-91022', full_name: '', same_requisition: true } })} actions={{ ...noop, canAct: false }} />
          </ul>
        </Section>

        <Section title="Field">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Email" htmlFor="f1" hint="We never show this to clients before the interview stage."><Input id="f1" placeholder="name@company.com" /></Field>
            <Field label="Password" htmlFor="f2" error="Enter your password"><Input id="f2" type="password" aria-invalid /></Field>
            <Field label="Stage" htmlFor="f3"><Select id="f3"><option>Screened</option></Select></Field>
            <Field label="Disabled" htmlFor="f4"><Input id="f4" disabled value="Read only" readOnly /></Field>
            <Field label="Note" htmlFor="f5" className="md:col-span-2"><Textarea id="f5" /></Field>
          </div>
        </Section>

        <Section title="EmptyState, Skeleton, ErrorState">
          <div className="grid gap-4 md:grid-cols-2">
            <EmptyState title="No CVs yet" action={<Button size="sm">Upload CVs</Button>}>Upload a batch of PDF or DOCX CVs. They are parsed and scored, best first.</EmptyState>
            <ErrorState error={new Error('Network request failed')} onRetry={() => {}} />
            <ListSkeleton rows={2} />
            <div className="space-y-2"><Skeleton className="h-6 w-1/2" /><Skeleton className="h-24 w-full" /></div>
          </div>
        </Section>

        <Section title="Toast and Dialog">
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => toast('Submitted to Northwind', 'ok')}>Success toast</Button>
            <Button variant="secondary" onClick={() => toast('Could not reach the AI service', 'bad')}>Error toast</Button>
            <Button variant="secondary" onClick={() => toast('Scoring queued', 'info')}>Info toast</Button>
            <Button variant="secondary" onClick={() => setDlg(true)}>Open dialog</Button>
          </div>
          <Dialog open={dlg} onClose={() => setDlg(false)} title="How we screen" description="What the AI does and does not do."><FairnessPanel /></Dialog>
        </Section>

        <Section title="FairnessPanel">
          <div className="grid gap-8 md:grid-cols-2">
            <FairnessPanel />
            <FairnessPanel variant="strip" className="!grid-cols-2 self-start" />
          </div>
        </Section>

        <Section title="GlassPanel and PillNav (showcase only)">
          <div className="showcase-canvas space-y-4 p-8">
            <PillNav items={[{ label: 'How we screen', onClick: () => {}, active: true }, { label: 'Privacy', onClick: () => {} }]} />
            <GlassPanel rule className="max-w-sm p-5"><p className="text-small text-text-2">Frosted panel with the hairline rule on top.</p></GlassPanel>
          </div>
        </Section>
    </div>
  )
}
