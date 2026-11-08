import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ChevronLeft, ChevronRight, CircleHelp, Eye, MoreHorizontal, Send, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'
import { AppShell } from '@/components/AppShell'
import { AnalysisPane, type Tab } from '@/components/candidate/analysis-pane'
import { CvPane } from '@/components/candidate/cv-pane'
import { ErrorState } from '@/components/states'
import { ScoreBadge, StageBadge } from '@/components/score'
import { Button } from '@/components/ui/button'
import { FieldError, Textarea } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Modal } from '@/components/ui/modal'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { post } from '@/lib/api'
import { useMe } from '@/lib/auth'
import { orderCriteria } from '@/lib/cv'
import { dateTime, notice, stageLabel, years } from '@/lib/format'
import { prefersReducedMotion } from '@/lib/motion'
import { useCandidate, useCandidateActions, useRanked } from '@/lib/queries'
import type { CandidateDetail, Stage } from '@/lib/types'
import { cn } from '@/lib/utils'

const NOT_OPENED = 'Open the CV first. You can submit a candidate once you have read their CV.'
const WRONG_STAGE = 'Only candidates at the Sourced or Screened stage can be submitted.'

function SubmitDialog({ c, open, onClose }: { c: CandidateDetail; open: boolean; onClose: () => void }) {
  const { submit } = useCandidateActions(c.id, c.requisition.id)
  const { toast } = useToast()
  const { register, handleSubmit } = useForm<{ note: string }>({ defaultValues: { note: '' } })
  return (
    <Modal open={open} onClose={onClose} title="Submit to client" description="The client sees this candidate with masked contact details. You decide; the score never submits anyone.">
      <form className="space-y-3" onSubmit={handleSubmit((v) => submit.mutate(v.note, { onSuccess: () => { toast('Submitted to the client with masked contacts', 'ok'); onClose() } }))}>
        <div className="space-y-1.5">
          <Label htmlFor="note">Note for the client (optional)</Label>
          <Textarea id="note" rows={2} maxLength={500} placeholder="Why this candidate fits" {...register('note')} />
        </div>
        <FieldError message={submit.isError ? submit.error.message : undefined} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" arrow loading={submit.isPending}>{submit.isPending ? 'Submitting' : 'Submit to client'}</Button>
        </div>
      </form>
    </Modal>
  )
}

const deleteSchema = z.object({ requester: z.string().trim().min(2, 'Who asked for the deletion?').max(120) })

function DeleteDialog({ c, open, onClose }: { c: CandidateDetail; open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { remove } = useCandidateActions(c.id, c.requisition.id)
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof deleteSchema>>({ resolver: zodResolver(deleteSchema), defaultValues: { requester: '' } })
  return (
    <Modal open={open} onClose={onClose} title="Delete this candidate’s data?" description="This wipes the CV file, extracted text, parsed fields and scores, and removes the candidate from every list and client portal. A tombstone (ID, date, requester) is kept. It cannot be undone.">
      <form className="space-y-3" onSubmit={handleSubmit((v) => remove.mutate(v.requester, { onSuccess: () => navigate(`/requisitions/${c.requisition.id}`, { replace: true }) }))}>
        <div className="space-y-1.5">
          <Label htmlFor="requester">Requested by</Label>
          <Input id="requester" placeholder="e.g. the candidate, by email" aria-invalid={!!errors.requester} {...register('requester')} />
          <FieldError message={errors.requester?.message} />
        </div>
        <FieldError message={remove.isError ? remove.error.message : undefined} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="destructive" disabled={remove.isPending}>{remove.isPending ? 'Deleting…' : 'Delete permanently'}</Button>
        </div>
      </form>
    </Modal>
  )
}

function SubmissionPanel({ c, canAct }: { c: CandidateDetail; canAct: boolean }) {
  const qc = useQueryClient()
  const respond = useMutation({
    mutationFn: (v: { id: number; status: 'confirmed' | 'declined' }) => post(`/api/slots/${v.id}/respond/`, { status: v.status }),
    onSuccess: (_d, v) =>
      qc.setQueryData<CandidateDetail>(['candidate', c.id], (old) =>
        old && old.submission ? { ...old, submission: { ...old.submission, slots: old.submission.slots.map((s) => (s.id === v.id ? { ...s, status: v.status } : s)) } } : old,
      ),
  })
  const sub = c.submission
  if (!sub) return null
  return (
    <section className="space-y-2">
      <h3 className="text-micro font-semibold uppercase text-text-2">Client</h3>
      <p>Submitted to the client on {dateTime(sub.submitted_at)}.</p>
      {sub.note && <p className="text-text-2">“{sub.note}”</p>}
      {sub.decisions.map((d, i) => (
        <p key={i} className="rounded-input bg-surface-2 p-2.5">
          <strong>{d.decision === 'shortlist' ? 'Client shortlisted' : 'Client rejected'}</strong> · {dateTime(d.at)}
          {d.reason && <span className="block text-text-2">Reason: {d.reason}</span>}
        </p>
      ))}
      {sub.slots.map((s) => (
        <div key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-input bg-surface-2 p-2.5">
          <span>Interview {dateTime(s.starts_at)} · {s.duration_minutes} min · <em className="not-italic text-text-2">{s.status}</em></span>
          {canAct && s.status === 'proposed' && (
            <span className="flex gap-1.5">
              <Button size="xs" onClick={() => respond.mutate({ id: s.id, status: 'confirmed' })} disabled={respond.isPending}>Confirm</Button>
              <Button size="xs" variant="outline" onClick={() => respond.mutate({ id: s.id, status: 'declined' })} disabled={respond.isPending}>Decline</Button>
            </span>
          )}
        </div>
      ))}
    </section>
  )
}

/** A small menu / popover: closes on Escape and outside click. */
function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const down = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && close()
    const key = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('mousedown', down)
    document.addEventListener('keydown', key)
    return () => {
      document.removeEventListener('mousedown', down)
      document.removeEventListener('keydown', key)
    }
  }, [open, close])
  return ref
}

const KEYS: [string, string][] = [['j / k', 'Next / previous candidate'], ['e', 'Expand the next criterion'], ['/', 'Find in the CV'], ['?', 'This list']]

function ShortcutHint() {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const ref = useDismiss(open, close)
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.key === '?' && !(e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))) setOpen((o) => !o)
    }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [])
  return (
    <div ref={ref} className="relative max-lg:hidden">
      <button type="button" aria-label="Keyboard shortcuts" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="grid size-9 place-items-center rounded-pill text-text-3 transition-colors duration-(--dur-fast) hover:bg-surface-2 hover:text-text-1">
        <CircleHelp className="size-4" aria-hidden />
      </button>
      {open && (
        <dl role="dialog" aria-label="Keyboard shortcuts" className="absolute right-0 top-full z-30 mt-2 w-64 space-y-2 rounded-card border bg-surface-2 p-3 text-small shadow-float">
          {KEYS.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-3">
              <dd className="text-text-2">{v}</dd>
              <dt><kbd className="tnum rounded-xs border px-1.5 py-0.5 text-micro text-text-1">{k}</kbd></dt>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

function MoreMenu({ c, onDelete }: { c: CandidateDetail; onDelete: () => void }) {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const ref = useDismiss(open, close)
  const { move } = useCandidateActions(c.id, c.requisition.id)
  const item = 'flex min-h-11 w-full items-center rounded-input px-3 text-left text-small hover:bg-surface-1 focus-visible:bg-surface-1'
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-haspopup="menu" aria-expanded={open} aria-label="More actions" onClick={() => setOpen((o) => !o)} className="inline-flex h-11 items-center gap-1.5 rounded-pill border border-border-strong px-3.5 text-small text-text-1 transition-colors duration-(--dur-fast) hover:bg-surface-2 lg:h-10">
        <MoreHorizontal className="size-4" aria-hidden /> <span className="max-sm:hidden">More</span>
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-30 mt-2 w-60 rounded-card border bg-surface-2 p-1.5 shadow-float">
          {c.allowed_moves.length > 0 && <p className="px-3 pb-1 pt-1.5 text-micro font-semibold uppercase text-text-2">Move stage</p>}
          {c.allowed_moves.map((m: Stage) => (
            <button key={m} role="menuitem" type="button" disabled={move.isPending} className={item} onClick={() => { move.mutate(m); close() }}>
              {stageLabel(m)}
            </button>
          ))}
          <div className="my-1 border-t" />
          <button role="menuitem" type="button" className={cn(item, 'text-bad')} onClick={() => { close(); onDelete() }}>Delete on request</button>
        </div>
      )}
    </div>
  )
}

const useNarrow = () => {
  const [narrow, setNarrow] = useState(() => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 1023px)').matches)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(max-width: 1023px)')
    const on = () => setNarrow(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return narrow
}

function Meta({ c }: { c: CandidateDetail }) {
  // only the fields that exist: a missing value is never shown as a dash
  const chips = [c.experience_years !== null && years(c.experience_years), c.notice_days !== null && `Notice ${notice(c.notice_days)}`, c.location].filter(Boolean) as string[]
  return chips.length ? (
    <ul className="flex flex-wrap gap-1.5">
      {chips.map((t) => <li key={t} className="rounded-pill border px-2.5 py-0.5 text-small text-text-2">{t}</li>)}
    </ul>
  ) : null
}

function Detail({ c }: { c: CandidateDetail }) {
  const { data: user } = useMe()
  const navigate = useNavigate()
  const canAct = user?.role === 'recruiter'
  const { retry } = useCandidateActions(c.id, c.requisition.id)
  const ranked = useRanked(c.requisition.id, {})
  const narrow = useNarrow()
  const { must, nice, all } = useMemo(() => orderCriteria(c.score.criteria), [c.score.criteria])
  const numbers = useMemo(() => new Map(all.map((k, i) => [k.criterion_id, i + 1])), [all])
  const [tab, setTab] = useState<Tab>('criteria')
  const [mobile, setMobile] = useState<'analysis' | 'cv'>('analysis')
  const [openId, setOpenId] = useState<number | null>(null)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [tick, setTick] = useState(0)
  const [submitOpen, setSubmitOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const findRef = useRef<HTMLInputElement>(null)

  const ids = ranked.data?.candidates.map((x) => x.id) ?? []
  const pos = ids.indexOf(c.id)
  const go = useCallback((d: number) => {
    const next = ids[pos + d]
    if (pos >= 0 && next) navigate(`/candidates/${next}`)
  }, [ids, pos, navigate])

  // hovering or focusing a criterion shows its quote in the CV (a short delay so sweeping the mouse does not thrash the scroll)
  const previewTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
  const preview = useCallback((id: number) => {
    clearTimeout(previewTimer.current)
    previewTimer.current = setTimeout(() => { setActiveId(id); setTick((t) => t + 1) }, prefersReducedMotion() ? 0 : 140)
  }, [])
  useEffect(() => () => clearTimeout(previewTimer.current), [])

  const open = (id: number | null) => {
    setOpenId(id)
    if (id === null) return
    setActiveId(id)
    if (narrow) { // phone: tapping a criterion shows its quote in the CV
      setMobile('cv')
      setTick((t) => t + 1)
    }
  }
  const fromCv = (id: number) => {
    setTab('criteria')
    setOpenId(id)
    setActiveId(id)
    if (narrow) setMobile('analysis')
    requestAnimationFrame(() => document.getElementById(`crit-${id}`)?.scrollIntoView({ block: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' }))
  }

  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      const t = e.target
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (t instanceof HTMLElement && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return
      if (document.querySelector('dialog[open]')) return
      if (e.key === 'j') go(1)
      else if (e.key === 'k') go(-1)
      else if (e.key === 'e' && all.length) {
        setTab('criteria')
        const i = all.findIndex((k) => k.criterion_id === openId)
        const next = all[(i + 1) % all.length].criterion_id
        setOpenId(next)
        setActiveId(next)
        setTick((n) => n + 1)
        requestAnimationFrame(() => document.getElementById(`crit-${next}`)?.scrollIntoView({ block: 'nearest' }))
      } else if (e.key === '/') {
        e.preventDefault()
        setMobile('cv')
        requestAnimationFrame(() => findRef.current?.focus())
      }
    }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [go, all, openId])

  const why = c.can_submit ? undefined : !c.viewed ? NOT_OPENED : WRONG_STAGE
  const sc = c.score
  const name = c.full_name || c.original_name || 'Unnamed CV'
  const active = all.find((k) => k.criterion_id === activeId)
  const submitBtn = canAct && !c.submission && (
    <Button arrow disabled={!!why} disabledReason={why} onClick={() => setSubmitOpen(true)} className="max-lg:h-12 max-lg:w-full">
      <Send aria-hidden /> Submit to client
    </Button>
  )
  const caption = active && (
    <div className="flex items-start justify-between gap-2 rounded-input bg-surface-1 px-3 py-2 text-small lg:hidden">
      <p className="min-w-0"><strong className="font-medium">{numbers.get(active.criterion_id)}. {active.name}</strong><span className="text-text-2"> · {active.evidence_status === 'verified' ? active.points : 'No evidence'}</span>{active.rationale && <span className="mt-0.5 block text-text-2">{active.rationale}</span>}</p>
      <button type="button" aria-label="Close" onClick={() => setActiveId(null)} className="grid size-8 shrink-0 place-items-center rounded-pill hover:bg-surface-2"><X className="size-4" aria-hidden /></button>
    </div>
  )

  return (
    <>
      <header className="shrink-0 space-y-2 border-b pb-3 lg:flex lg:min-h-[72px] lg:items-center lg:justify-between lg:gap-4 lg:space-y-0">
        <div className="flex min-w-0 items-center gap-3">
          <Link to={`/requisitions/${c.requisition.id}`} aria-label={`Back to ${c.requisition.title}`} title={c.requisition.title} className="grid size-11 shrink-0 place-items-center rounded-pill border border-border-strong text-text-2 transition-colors duration-(--dur-fast) hover:bg-surface-2 hover:text-text-1 lg:size-10">
            <ArrowLeft className="size-4" aria-hidden />
          </Link>
          <div className="min-w-0 space-y-1">
            <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
              <h1 className="truncate text-h2 lg:text-h1">{name}</h1>
              <StageBadge stage={c.stage} />
            </div>
            <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 text-small text-text-2 max-sm:[&_ul]:hidden">
              {c.current_role && <span className="truncate">{c.current_role}</span>}
              <Meta c={c} />
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3 max-lg:justify-between">
          <ScoreBadge score={sc} size="hdr" />
          {pos >= 0 && (
            <div className="flex items-center gap-1" role="group" aria-label="Candidates in this requisition">
              <button type="button" aria-label="Previous candidate (k)" disabled={pos === 0} onClick={() => go(-1)} className="grid size-9 place-items-center rounded-pill hover:bg-surface-2 disabled:opacity-40"><ChevronLeft className="size-4" aria-hidden /></button>
              <span className="tnum whitespace-nowrap text-small text-text-2">{pos + 1} of {ids.length}</span>
              <button type="button" aria-label="Next candidate (j)" disabled={pos >= ids.length - 1} onClick={() => go(1)} className="grid size-9 place-items-center rounded-pill hover:bg-surface-2 disabled:opacity-40"><ChevronRight className="size-4" aria-hidden /></button>
            </div>
          )}
          <div className="flex items-center gap-2">
            <span className="max-lg:hidden">{submitBtn}</span>
            {canAct && <MoreMenu c={c} onDelete={() => setDeleteOpen(true)} />}
            <ShortcutHint />
          </div>
        </div>
      </header>

      <div role="tablist" aria-label="Candidate panes" className="my-2 grid shrink-0 grid-cols-2 gap-1 rounded-pill border p-1 lg:hidden">
        {(['analysis', 'cv'] as const).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={mobile === t} onClick={() => setMobile(t)} className={cn('h-11 rounded-pill text-small transition-colors duration-(--dur-fast)', mobile === t ? 'bg-accent font-medium text-on-accent' : 'text-text-2')}>
            {t === 'cv' ? 'CV' : 'Analysis'}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 gap-6 pt-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <section aria-label="CV" className={cn('min-h-0 overflow-y-auto pb-24 lg:block lg:pb-6', mobile === 'cv' ? 'flex flex-col' : 'hidden')}>
          <CvPane c={c} numbers={numbers} activeId={activeId} focusTick={tick} onSelect={fromCv} findRef={findRef} caption={caption} />
        </section>
        <aside aria-label="Analysis" className={cn('min-h-0 flex-col lg:flex', mobile === 'analysis' ? 'flex' : 'hidden')}>
          <AnalysisPane
            c={c}
            must={must}
            nice={nice}
            numbers={numbers}
            tab={tab}
            onTab={setTab}
            openId={openId}
            activeId={activeId}
            onOpen={open}
            onPreview={preview}
            retry={canAct && <Button size="sm" variant="outline" onClick={() => retry.mutate()} disabled={retry.isPending || retry.isSuccess}>{retry.isSuccess ? 'Queued: refresh in a moment' : 'Retry scoring'}</Button>}
            submission={<SubmissionPanel c={c} canAct={canAct} />}
          />
        </aside>
      </div>

      {submitBtn && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t bg-ws px-(--gutter) pt-3 pb-[calc(0.75rem+var(--safe-bottom))] lg:hidden">
          <p className="mb-2 flex items-center gap-1.5 text-micro text-text-2"><Eye className="size-3.5" aria-hidden />{c.viewed ? 'You have opened this CV.' : 'You have not opened this CV yet.'}</p>
          {submitBtn}
        </div>
      )}
      {canAct && <SubmitDialog c={c} open={submitOpen} onClose={() => setSubmitOpen(false)} />}
      {canAct && <DeleteDialog c={c} open={deleteOpen} onClose={() => setDeleteOpen(false)} />}
    </>
  )
}

function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading candidate" className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-[72px] items-center justify-between gap-4 border-b pb-3">
        <div className="flex items-center gap-3"><Skeleton className="size-10 rounded-pill" /><div className="space-y-2"><Skeleton className="h-6 w-56" /><Skeleton className="h-4 w-72" /></div></div>
        <Skeleton className="size-16 rounded-pill" />
      </div>
      <div className="grid min-h-0 flex-1 gap-6 pt-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="cv-sheet mx-auto w-full max-w-[70ch] space-y-3 p-10 max-lg:hidden">
          {[0.5, 0.9, 0.8, 0.95, 0.6, 0.85, 0.7, 0.9, 0.4, 0.8, 0.95, 0.7].map((w, i) => <div key={i} className="h-3 animate-pulse rounded bg-paper-ink/10" style={{ width: `${w * 100}%` }} />)}
        </div>
        <div className="space-y-3">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-10 w-full rounded-pill" />
          {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      </div>
    </div>
  )
}

export function CandidatePage() {
  const { id = '' } = useParams()
  const query = useCandidate(id)
  return (
    <AppShell fill>
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <header className="flex min-h-[72px] shrink-0 items-center gap-3 border-b pb-3">
            <Link to="/requisitions" aria-label="Back to requisitions" className="grid size-10 place-items-center rounded-pill border border-border-strong text-text-2 hover:bg-surface-2 hover:text-text-1"><ArrowLeft className="size-4" aria-hidden /></Link>
            <h1 className="text-h2">Candidate</h1>
          </header>
          <ErrorState className="mt-6" error={query.error} onRetry={() => query.refetch()} />
        </div>
      ) : (
        <Detail key={query.data.id} c={query.data} />
      )}
    </AppShell>
  )
}
