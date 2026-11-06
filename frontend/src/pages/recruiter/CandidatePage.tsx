import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Copy, ExternalLink, Eye, FileText, ScanLine, Send, ShieldCheck, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'
import { AppShell, PageHeader } from '@/components/AppShell'
import { EvidenceList, ScoreBadge, StageBadge } from '@/components/score'
import { Async, Skeleton } from '@/components/states'
import { Button } from '@/components/ui/button'
import { FieldError, Hint, Select, Textarea } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from '@/components/ui/modal'
import { post } from '@/lib/api'
import { useMe } from '@/lib/auth'
import { dateTime, notice, stageLabel, years } from '@/lib/format'
import { useCandidate, useCandidateActions } from '@/lib/queries'
import type { CandidateDetail, CriterionScore, Stage } from '@/lib/types'
import { cn } from '@/lib/utils'

function Highlighted({ text, criteria, activeId }: { text: string; criteria: CriterionScore[]; activeId: number | null }) {
  const parts = useMemo(() => {
    const spans = criteria
      .filter((c) => c.span)
      .map((c) => ({ id: c.criterion_id, start: c.span![0], end: c.span![1] }))
      .sort((a, b) => a.start - b.start)
    const out: { text: string; id?: number }[] = []
    let at = 0
    for (const s of spans) {
      if (s.start < at) continue // overlapping quotes: keep the first
      if (s.start > at) out.push({ text: text.slice(at, s.start) })
      out.push({ text: text.slice(s.start, s.end), id: s.id })
      at = s.end
    }
    if (at < text.length) out.push({ text: text.slice(at) })
    return out
  }, [text, criteria])
  return (
    <>
      {parts.map((p, i) =>
        p.id ? (
          <mark key={i} id={`ev-${p.id}`} className="evidence" data-active={activeId === p.id}>
            {p.text}
          </mark>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </>
  )
}

function SubmitPanel({ c }: { c: CandidateDetail }) {
  const { submit } = useCandidateActions(c.id, c.requisition.id)
  const { register, handleSubmit } = useForm<{ note: string }>({ defaultValues: { note: '' } })
  return (
    <form className="space-y-3" onSubmit={handleSubmit((v) => submit.mutate(v.note))}>
      <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <Eye className="size-4 text-primary" aria-hidden /> You have opened this CV, so you can submit it.
      </p>
      <div className="space-y-1.5">
        <Label htmlFor="note">Note for the client (optional)</Label>
        <Textarea id="note" rows={2} maxLength={500} placeholder="Why this candidate fits" {...register('note')} />
      </div>
      <FieldError message={submit.isError ? submit.error.message : undefined} />
      <Button type="submit" className="w-full" disabled={!c.can_submit || submit.isPending}>
        <Send /> {submit.isPending ? 'Submitting…' : 'Submit to client'}
      </Button>
      <Hint>The client sees this candidate with masked contact details. You decide; the score never submits anyone.</Hint>
    </form>
  )
}

const deleteSchema = z.object({ requester: z.string().trim().min(2, 'Who asked for the deletion?').max(120) })

function DeletePanel({ c }: { c: CandidateDetail }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { remove } = useCandidateActions(c.id, c.requisition.id)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof deleteSchema>>({ resolver: zodResolver(deleteSchema), defaultValues: { requester: '' } })
  return (
    <>
      <Button variant="destructive" size="sm" onClick={() => setOpen(true)}>
        <Trash2 /> Delete on request
      </Button>
      <Modal open={open} onClose={() => setOpen(false)} title="Delete this candidate’s data?" description="This wipes the CV file, extracted text, parsed fields and scores, and removes the candidate from every list and client portal. A tombstone (ID, date, requester) is kept. It cannot be undone.">
        <form
          className="space-y-3"
          onSubmit={handleSubmit((v) => remove.mutate(v.requester, { onSuccess: () => navigate(`/requisitions/${c.requisition.id}`, { replace: true }) }))}
        >
          <div className="space-y-1.5">
            <Label htmlFor="requester">Requested by</Label>
            <Input id="requester" placeholder="e.g. the candidate, by email" aria-invalid={!!errors.requester} {...register('requester')} />
            <FieldError message={errors.requester?.message} />
          </div>
          <FieldError message={remove.isError ? remove.error.message : undefined} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="destructive" disabled={remove.isPending}>{remove.isPending ? 'Deleting…' : 'Delete permanently'}</Button>
          </div>
        </form>
      </Modal>
    </>
  )
}

function SubmissionPanel({ c, canAct }: { c: CandidateDetail; canAct: boolean }) {
  const qc = useQueryClient()
  const respond = useMutation({
    mutationFn: (v: { id: number; status: 'confirmed' | 'declined' }) => post(`/api/slots/${v.id}/respond/`, { status: v.status }),
    onSuccess: (_d, v) =>
      qc.setQueryData<CandidateDetail>(['candidate', c.id], (old) =>
        old && old.submission
          ? { ...old, submission: { ...old.submission, slots: old.submission.slots.map((s) => (s.id === v.id ? { ...s, status: v.status } : s)) } }
          : old,
      ),
  })
  const sub = c.submission!
  return (
    <div className="space-y-3 text-sm">
      <p>Submitted to the client on {dateTime(sub.submitted_at)}.</p>
      {sub.note && <p className="text-muted-foreground">“{sub.note}”</p>}
      {sub.decisions.map((d, i) => (
        <p key={i} className="rounded-lg bg-muted/60 p-2.5">
          <strong>{d.decision === 'shortlist' ? 'Client shortlisted' : 'Client rejected'}</strong> · {dateTime(d.at)}
          {d.reason && <span className="block text-muted-foreground">Reason: {d.reason}</span>}
        </p>
      ))}
      {sub.slots.map((s) => (
        <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-accent/50 p-2.5">
          <span>
            Interview {dateTime(s.starts_at)} · {s.duration_minutes} min · <em className="not-italic text-muted-foreground">{s.status}</em>
          </span>
          {canAct && s.status === 'proposed' && (
            <span className="flex gap-1.5">
              <Button size="xs" onClick={() => respond.mutate({ id: s.id, status: 'confirmed' })} disabled={respond.isPending}>Confirm</Button>
              <Button size="xs" variant="outline" onClick={() => respond.mutate({ id: s.id, status: 'declined' })} disabled={respond.isPending}>Decline</Button>
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

function Detail({ c }: { c: CandidateDetail }) {
  const { data: user } = useMe()
  const canAct = user?.role === 'recruiter'
  const { move, retry } = useCandidateActions(c.id, c.requisition.id)
  const [activeId, setActiveId] = useState<number | null>(null)
  const noText = c.raw_text.trim().length === 0
  const select = (crit: CriterionScore) => {
    setActiveId(crit.criterion_id)
    document.getElementById(`ev-${crit.criterion_id}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
  const sc = c.score
  return (
    <>
      <PageHeader
        back={{ to: `/requisitions/${c.requisition.id}`, label: c.requisition.title }}
        title={c.full_name || c.original_name || 'Unnamed CV'}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            {[c.current_role, years(c.experience_years), `notice ${notice(c.notice_days)}`, c.location].filter(Boolean).join(' · ')}
            <StageBadge stage={c.stage} />
          </span>
        }
        actions={<ScoreBadge score={sc} size="lg" />}
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_23rem]">
        <section aria-label="CV" className="order-2 min-w-0 lg:order-1">
          <div className="mb-2 flex items-center justify-between gap-3">
            <h2 className="flex items-center gap-1.5 font-medium"><FileText className="size-4" aria-hidden /> CV text</h2>
            {c.cv_file_url && (
              <a href={c.cv_file_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                Open original {c.cv_file_kind?.toUpperCase()} <ExternalLink className="size-3.5" aria-hidden />
              </a>
            )}
          </div>
          {noText ? (
            <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed p-10 text-center">
              <ScanLine className="size-6 text-muted-foreground" aria-hidden />
              <p className="font-medium">Needs manual review</p>
              <p className="max-w-sm text-sm text-muted-foreground">This file has no readable text (scanned or image-only), so it was not scored. Open the original and judge it yourself. It is not rejected or hidden.</p>
            </div>
          ) : (
            <pre className="max-h-[75vh] overflow-auto whitespace-pre-wrap break-words rounded-xl border bg-card p-4 font-sans text-sm leading-relaxed">
              <Highlighted text={c.raw_text} criteria={sc.criteria} activeId={activeId} />
            </pre>
          )}
        </section>

        <aside className="order-1 space-y-5 lg:order-2" aria-label="Screening">
          <section className="space-y-3">
            <h2 className="font-medium">Why this score</h2>
            {sc.state === 'scored' && <EvidenceList criteria={sc.criteria} activeId={activeId} onSelect={select} />}
            {sc.state === 'failed' && (
              <div role="alert" className="space-y-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm">
                <p className="font-medium">Scoring failed, retry</p>
                <p className="text-muted-foreground">{sc.error || 'The AI could not score this CV.'} The CV is still here to read.</p>
                {canAct && <Button size="sm" variant="outline" onClick={() => retry.mutate()} disabled={retry.isPending || retry.isSuccess}>{retry.isSuccess ? 'Queued: refresh in a moment' : 'Retry scoring'}</Button>}
              </div>
            )}
            {['needs_manual_review', 'cv_failed', 'processing', 'pending', 'no_scorecard'].includes(sc.state) && (
              <p className="rounded-xl border border-dashed p-3 text-sm text-muted-foreground">
                {sc.state === 'needs_manual_review' && 'No score: a person needs to read this one.'}
                {sc.state === 'cv_failed' && (sc.error || 'The file could not be read. Upload it again.')}
                {(sc.state === 'processing' || sc.state === 'pending') && 'Still being processed. Check back in a few seconds.'}
                {sc.state === 'no_scorecard' && 'Add a scorecard to score this CV.'}
              </p>
            )}
            {sc.state === 'scored' && <Hint>Scored with {sc.model || 'AI'} against scorecard v{sc.scorecard_version}. Name, gender, age, photo and marital status were removed before scoring.</Hint>}
          </section>

          <section className="space-y-3 rounded-xl border p-4">
            <h2 className="font-medium">Next step</h2>
            {c.submission ? (
              <SubmissionPanel c={c} canAct={canAct} />
            ) : canAct ? (
              <SubmitPanel c={c} />
            ) : (
              <p className="text-sm text-muted-foreground">Not submitted yet.</p>
            )}
            {canAct && c.allowed_moves.length > 0 && (
              <div className="space-y-1.5 border-t pt-3">
                <Label htmlFor="move">Move in pipeline</Label>
                <Select id="move" value="" disabled={move.isPending} onChange={(e) => e.target.value && move.mutate(e.target.value as Stage)}>
                  <option value="">Currently {stageLabel(c.stage)}…</option>
                  {c.allowed_moves.map((m) => <option key={m} value={m}>{stageLabel(m)}</option>)}
                </Select>
                <FieldError message={move.isError ? move.error.message : undefined} />
              </div>
            )}
          </section>

          <section className="space-y-2 rounded-xl border p-4 text-sm">
            <h2 className="font-medium">Contact</h2>
            <p>{c.email || '—'}</p>
            <p>{c.phone || '—'}</p>
            <p className="text-xs text-muted-foreground">Clients see these masked until the interview stage.</p>
          </section>

          {c.duplicate_of && (
            <p className="flex items-start gap-2 rounded-xl bg-muted/60 p-3 text-sm">
              <Copy className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>
                Possible duplicate of{' '}
                <Link className="underline" to={`/candidates/${c.duplicate_of.id}`}>{c.duplicate_of.full_name || c.duplicate_of.external_id}</Link>
                {c.duplicate_of.same_requisition ? '' : ' (another requisition)'}. {c.cv_note.replace(/^Possible duplicate of [^(]*/, '')}
              </span>
            </p>
          )}

          <section className="space-y-3 rounded-xl border p-4 text-sm">
            <h2 className="flex items-center gap-1.5 font-medium"><ShieldCheck className="size-4 text-primary" aria-hidden /> Consent and access</h2>
            {c.consent.map((k, i) => (
              <p key={i}>
                Consent recorded {dateTime(k.recorded_at)}: {k.source.toLowerCase()}{k.recorded_by && ` (${k.recorded_by})`}. Purpose: hiring use only.
              </p>
            ))}
            <div>
              <p className="font-medium">Opened {c.view_log.total} time{c.view_log.total === 1 ? '' : 's'}</p>
              <ul className="mt-1 space-y-0.5 text-muted-foreground">
                {c.view_log.recent.slice(0, 5).map((v, i) => (
                  <li key={i}>{v.user} · {v.kind === 'cv' ? 'file' : 'profile'} · {dateTime(v.at)}</li>
                ))}
              </ul>
            </div>
            {canAct && <DeletePanel c={c} />}
          </section>

          {c.stage_events.length > 0 && (
            <section className="space-y-2 text-sm">
              <h2 className="font-medium">History</h2>
              <ol className={cn('space-y-1 border-l pl-3 text-muted-foreground')}>
                {c.stage_events.map((e, i) => (
                  <li key={i}>
                    {stageLabel(e.to)} <span className="text-xs">· {e.by} · {dateTime(e.at)}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </aside>
      </div>
    </>
  )
}

export function CandidatePage() {
  const { id = '' } = useParams()
  const query = useCandidate(id)
  return (
    <AppShell>
      <Async query={query} skeleton={<div className="space-y-4"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-96 w-full" /></div>}>
        {(c) => <Detail c={c} />}
      </Async>
    </AppShell>
  )
}
