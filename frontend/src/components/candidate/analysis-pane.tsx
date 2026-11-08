import { Check, ChevronRight, Contrast, Copy, Minus } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { BandPill } from '@/components/score'
import { ctcFromText, locate, needsCheck, statusOf, summarise, type Status } from '@/lib/cv'
import { dateTime, notice, stageLabel, years } from '@/lib/format'
import type { CandidateDetail, CriterionScore } from '@/lib/types'
import { cn } from '@/lib/utils'

export type Tab = 'criteria' | 'profile' | 'activity'
const TABS: { key: Tab; label: string }[] = [
  { key: 'criteria', label: 'Criteria' },
  { key: 'profile', label: 'Profile' },
  { key: 'activity', label: 'Activity' },
]

const ICON: Record<Status, { Icon: typeof Check; label: string; tone: string }> = {
  met: { Icon: Check, label: 'Verified evidence', tone: 'text-ok' },
  partial: { Icon: Contrast, label: 'Partial match', tone: 'text-warn' },
  none: { Icon: Minus, label: 'No evidence found', tone: 'text-text-3' },
}

/** Quote clamped to 3 lines; an inline "More" appears only when it is actually cut. */
function Quote({ text }: { text: string }) {
  const ref = useRef<HTMLQuoteElement>(null)
  const [open, setOpen] = useState(false)
  const [cut, setCut] = useState(false)
  useLayoutEffect(() => {
    const el = ref.current
    if (el && !open) setCut(el.scrollHeight > el.clientHeight + 1)
  }, [text, open])
  return (
    <blockquote ref={ref} className={cn('border-l-2 border-border-strong pl-3 text-body text-text-1', !open && 'line-clamp-3')}>
      “{text}”
      {(cut || open) && (
        <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="ml-2 text-small text-signal hover:underline">
          {open ? 'Less' : 'More'}
        </button>
      )}
    </blockquote>
  )
}

function Row({ c, n, text, open, active, onToggle, onPreview }: { c: CriterionScore; n: number; text: string; open: boolean; active: boolean; onToggle: () => void; onPreview: () => void }) {
  const st = statusOf(c)
  const { Icon, label, tone } = ICON[st]
  const none = c.evidence_status === 'no_evidence'
  const check = needsCheck(c)
  return (
    <li id={`crit-${c.criterion_id}`} className={cn('border-b last:border-b-0', (open || active) && 'bg-surface-2')}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={`crit-body-${c.criterion_id}`}
        onClick={onToggle}
        onMouseEnter={onPreview}
        onFocus={onPreview}
        className="grid min-h-12 w-full grid-cols-[1.25rem_1.25rem_minmax(0,1fr)_auto_3.5rem_2.25rem] items-center gap-x-2 px-3 py-2 text-left max-sm:min-h-14 max-sm:grid-cols-[1.25rem_1.25rem_minmax(0,1fr)_auto_2.25rem]"
      >
        <span className="tnum text-micro font-semibold text-text-2" aria-label={`Criterion ${n}`}>{n}</span>
        <Icon className={cn('size-4', tone)} role="img" aria-label={label} />
        <span className="truncate text-body">{c.name}</span>
        {check ? <span className="rounded-pill border border-warn/40 px-2 py-0.5 text-micro font-medium uppercase text-warn">Check</span> : <span />}
        <span aria-hidden className="h-[3px] w-full overflow-hidden rounded-pill bg-track max-sm:hidden"><span className="block h-full rounded-pill bg-text-1/70" style={{ width: `${none ? 0 : Math.max(0, Math.min(100, c.points))}%` }} /></span>
        <span className="tnum text-right text-body font-medium">{none ? '–' : c.points}</span>
      </button>
      {open && (
        <div id={`crit-body-${c.criterion_id}`} className="space-y-2 px-3 pb-4 pl-[3.75rem] max-sm:pl-3">
          {none ? (
            <p className="rounded-input border border-dashed px-3 py-2 text-small text-text-2">No evidence found in this CV. The criterion is shown as such, never guessed.</p>
          ) : (
            <>
              <p className="flex flex-wrap items-center gap-x-3 text-micro uppercase text-text-2">
                <span className="inline-flex items-center gap-1.5">
                  <span aria-hidden className={cn('size-1.5 rounded-pill', c.unverified ? 'bg-warn' : 'bg-ok')} />
                  {c.unverified ? 'Unverified' : 'Verified in CV'}
                </span>
                <span>{locate(text, c.span?.[0] ?? 0)}</span>
              </p>
              <Quote text={c.quote} />
            </>
          )}
          {c.rationale && <p className="text-small text-text-2">{c.rationale}</p>}
        </div>
      )}
    </li>
  )
}

function Group({ label, rows, numbers, text, openId, activeId, onOpen, onPreview }: { label: string; rows: CriterionScore[]; numbers: Map<number, number>; text: string; openId: number | null; activeId: number | null; onOpen: (id: number | null) => void; onPreview: (id: number) => void }) {
  if (!rows.length) return null
  return (
    <section aria-label={label} className="space-y-1.5">
      <h3 className="px-1 text-micro font-semibold uppercase text-text-2">{label}</h3>
      <ul className="overflow-hidden rounded-card border bg-surface-1">
        {rows.map((c) => (
          <Row key={c.criterion_id} c={c} n={numbers.get(c.criterion_id)!} text={text} open={openId === c.criterion_id} active={activeId === c.criterion_id} onToggle={() => onOpen(openId === c.criterion_id ? null : c.criterion_id)} onPreview={() => onPreview(c.criterion_id)} />
        ))}
      </ul>
    </section>
  )
}

const NOT_STATED = <span className="text-text-3">Not stated</span>

function Profile({ c }: { c: CandidateDetail }) {
  const rows: [string, React.ReactNode][] = [
    ['Current role', c.current_role || NOT_STATED],
    ['Experience', c.experience_years !== null ? years(c.experience_years) : NOT_STATED],
    ['Notice', c.notice_days !== null ? notice(c.notice_days) : NOT_STATED],
    ['Location', c.location || NOT_STATED],
    ['Current CTC', ctcFromText(c.raw_text, 'current') ?? NOT_STATED],
    ['Expected CTC', ctcFromText(c.raw_text, 'expected') ?? NOT_STATED],
    ['Email', c.email ? <span className="tnum break-all">{c.email}</span> : NOT_STATED],
    ['Phone', c.phone ? <span className="tnum">{c.phone}</span> : NOT_STATED],
  ]
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-[7.5rem_minmax(0,1fr)] gap-x-4 gap-y-3 text-body">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-small text-text-2">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="space-y-2">
        <h3 className="text-small text-text-2">Skills</h3>
        {c.skills.length ? (
          <ul className="flex flex-wrap gap-1.5">
            {c.skills.map((s) => <li key={s} className="rounded-pill border px-2.5 py-1 text-small">{s}</li>)}
          </ul>
        ) : (
          <p>{NOT_STATED}</p>
        )}
      </div>
      <p className="text-small text-text-3">Clients see email and phone masked until the interview stage.</p>
    </div>
  )
}

function Activity({ c, submission }: { c: CandidateDetail; submission: React.ReactNode }) {
  return (
    <div className="space-y-6 text-small">
      {submission}
      {c.duplicate_of && (
        <p className="flex items-start gap-2 rounded-input bg-surface-2 p-3">
          <Copy className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            Possible duplicate of <Link className="underline" to={`/candidates/${c.duplicate_of.id}`}>{c.duplicate_of.full_name || c.duplicate_of.external_id}</Link>
            {c.duplicate_of.same_requisition ? '' : ' (another requisition)'}. {c.cv_note.replace(/^Possible duplicate of [^(]*/, '')}
          </span>
        </p>
      )}
      <section className="space-y-2">
        <h3 className="text-micro font-semibold uppercase text-text-2">Consent</h3>
        {c.consent.length ? c.consent.map((k, i) => (
          <p key={i}>Recorded {dateTime(k.recorded_at)}: {k.source.toLowerCase()}{k.recorded_by && ` (${k.recorded_by})`}. Purpose: hiring use only.</p>
        )) : <p className="text-text-3">No consent record.</p>}
      </section>
      <section className="space-y-2">
        <h3 className="text-micro font-semibold uppercase text-text-2">Opened {c.view_log.total} time{c.view_log.total === 1 ? '' : 's'}</h3>
        <ul className="space-y-1 text-text-2">
          {c.view_log.recent.slice(0, 6).map((v, i) => <li key={i} className="tnum">{v.user} · {v.kind === 'cv' ? 'file' : 'profile'} · {dateTime(v.at)}</li>)}
        </ul>
      </section>
      {c.stage_events.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-micro font-semibold uppercase text-text-2">History</h3>
          <ol className="space-y-2 border-l pl-4">
            {[...c.stage_events].reverse().map((e, i) => (
              <li key={i} className="relative">
                <span aria-hidden className="absolute -left-[1.3rem] top-1.5 size-2 rounded-pill bg-border-strong" />
                <span className="text-text-1">{stageLabel(e.to)}</span> <span className="tnum text-text-2">· {e.by} · {dateTime(e.at)}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}

interface Props {
  c: CandidateDetail
  must: CriterionScore[]
  nice: CriterionScore[]
  numbers: Map<number, number>
  tab: Tab
  onTab: (t: Tab) => void
  openId: number | null
  activeId: number | null
  onOpen: (id: number | null) => void
  onPreview: (id: number) => void
  retry?: React.ReactNode
  submission: React.ReactNode
}

/** Right pane: a quiet summary, then Criteria | Profile | Activity. The score itself lives once, in the header ring. */
export function AnalysisPane({ c, must, nice, numbers, tab, onTab, openId, activeId, onOpen, onPreview, retry, submission }: Props) {
  const sc = c.score
  const scored = sc.state === 'scored'
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="shrink-0 space-y-3 pb-3">
        <div className="space-y-1">
          <p className="flex items-baseline gap-2 max-lg:hidden">
            {scored && sc.band ? <BandPill band={sc.band} className="text-body" /> : null}
            {scored && <span className="tnum text-h2">{Math.round(sc.total ?? 0)}<span className="text-small text-text-2"> / 100</span></span>}
          </p>
          <p className="text-body text-text-1">
            {scored ? summarise(sc.criteria) : sc.state === 'failed' ? 'Scoring failed. The CV is still here to read.' : sc.state === 'needs_manual_review' ? 'No score: a person needs to read this one.' : sc.state === 'cv_failed' ? sc.error || 'The file could not be read.' : sc.state === 'no_scorecard' ? 'Add a scorecard to score this CV.' : 'Still being processed.'}
          </p>
          <p className="text-small text-text-2">Scores guide reading order; they never reject.</p>
        </div>
        {sc.state === 'failed' && retry}
        <div role="tablist" aria-label="Analysis sections" className="grid grid-cols-3 gap-1 rounded-pill border p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              id={`tab-${t.key}`}
              aria-selected={tab === t.key}
              aria-controls={`panel-${t.key}`}
              onClick={() => onTab(t.key)}
              className={cn('h-9 rounded-pill text-small transition-colors duration-(--dur-fast) max-sm:h-11', tab === t.key ? 'bg-accent font-medium text-on-accent' : 'text-text-2 hover:text-text-1')}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="min-h-0 flex-1 overflow-y-auto pb-24 pr-1 lg:pb-6">
        {tab === 'criteria' &&
          (scored ? (
            <div className="space-y-4">
              <Group label="Must-have" rows={must} numbers={numbers} text={c.raw_text} openId={openId} activeId={activeId} onOpen={onOpen} onPreview={onPreview} />
              <Group label="Nice-to-have" rows={nice} numbers={numbers} text={c.raw_text} openId={openId} activeId={activeId} onOpen={onOpen} onPreview={onPreview} />
              <p className="flex items-center gap-1 px-1 text-small text-text-3"><ChevronRight className="size-3.5" aria-hidden />Scored with {sc.model?.startsWith('offline') ? 'the built-in rule-based scorer (offline mode, no AI model)' : sc.model || 'AI'} against scorecard v{sc.scorecard_version}. Name, gender, age, photo and marital status were removed before scoring.</p>
            </div>
          ) : (
            <p className="rounded-card border border-dashed p-4 text-small text-text-2">There are no criteria scores for this CV yet.</p>
          ))}
        {tab === 'profile' && <Profile c={c} />}
        {tab === 'activity' && <Activity c={c} submission={submission} />}
      </div>
    </div>
  )
}
