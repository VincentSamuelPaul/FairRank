import { FileUp, RotateCw, ShieldCheck, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Spinner } from '@/components/states'
import { Button, buttonVariants } from '@/components/ui/button'
import { StatusChip, type ChipTone } from '@/components/ui/status-chip'
import { useToast } from '@/components/ui/toast'
import { api } from '@/lib/api'
import { CountUp } from '@/lib/motion'
import { uploadBatch, useRetryScoring, useUploadStatus } from '@/lib/queries'
import type { UploadItem } from '@/lib/types'
import { cn } from '@/lib/utils'

const MAX_BYTES = 5 * 1024 * 1024
const CHUNK = 25

interface Skipped { name: string; reason: string }
type Tone = 'ok' | 'warn' | 'info' | 'bad' | 'busy'
interface Look { label: string; tone: Tone; chip: ChipTone; pct: number; detail?: string; retry?: 'rescore' }

/** What a file's status means, how far along it is, and what (if anything) can be retried. */
function look(item?: UploadItem): Look {
  if (!item) return { label: 'Queued', tone: 'busy', chip: 'neutral', pct: 10 }
  if (item.cv_status === 'failed') return { label: 'Failed', tone: 'bad', chip: 'bad', pct: 100, detail: item.note }
  if (item.cv_status === 'needs_review') return { label: 'Needs review', tone: 'info', chip: 'info', pct: 100, detail: 'No readable text. It will not be scored, and it is not rejected.' }
  if (item.cv_status === 'queued') return { label: 'Parsing', tone: 'busy', chip: 'neutral', pct: 30 }
  const scoring = item.score_state === 'pending' || item.score_state === 'processing'
  if (item.cv_status === 'duplicate') return { label: scoring ? 'Duplicate · scoring' : 'Duplicate', tone: scoring ? 'busy' : 'warn', chip: 'warn', pct: scoring ? 70 : 100, detail: item.note }
  if (scoring) return { label: 'Scoring', tone: 'busy', chip: 'info', pct: 65 }
  if (item.score_state === 'failed') return { label: 'Scoring failed', tone: 'bad', chip: 'bad', pct: 100, detail: 'The CV is saved and readable. Retry scoring.', retry: 'rescore' }
  return { label: 'Scored', tone: 'ok', chip: 'ok', pct: 100 }
}

const BAR: Record<Tone, string> = { ok: 'bg-ok', warn: 'bg-warn', info: 'bg-info', bad: 'bg-bad', busy: 'bg-signal' }
const size = (n: number) => (n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`)

function FileProgress({ pct, tone, label }: { pct: number; tone: Tone; label: string }) {
  return (
    <div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="h-1 overflow-hidden rounded-pill bg-surface-2">
      <div className={cn('h-full rounded-pill transition-[width] duration-(--dur-base) ease-ui', BAR[tone])} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function UploadPage() {
  const { id = '' } = useParams()
  const input = useRef<HTMLInputElement>(null)
  const kept = useRef(new Map<string, File>()) // so a rejected file can be retried without choosing it again
  const { toast } = useToast()
  const rescore = useRetryScoring()
  const [files, setFiles] = useState<File[]>([])
  const [skipped, setSkipped] = useState<Skipped[]>([])
  const [consent, setConsent] = useState(false)
  const [drag, setDrag] = useState(false)
  const [sent, setSent] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [accepted, setAccepted] = useState<{ candidate_id: string; name: string }[]>([])
  const [rejected, setRejected] = useState<Skipped[]>([])
  const [retrying, setRetrying] = useState<string | null>(null)
  const ids = useMemo(() => accepted.map((a) => a.candidate_id), [accepted])
  const status = useUploadStatus(id, ids)

  function add(list: FileList | File[]) {
    const ok: File[] = []
    const bad: Skipped[] = []
    for (const f of Array.from(list)) {
      if (!/\.(pdf|docx)$/i.test(f.name)) bad.push({ name: f.name, reason: 'Only PDF or DOCX files' })
      else if (f.size > MAX_BYTES) bad.push({ name: f.name, reason: 'Larger than 5 MB' })
      else ok.push(f)
    }
    setFiles((prev) => [...prev, ...ok].slice(0, 500))
    setSkipped((prev) => [...prev, ...bad])
  }

  async function send(batch: File[]) {
    batch.forEach((f) => kept.current.set(f.name, f))
    const acc: typeof accepted = []
    const rej: Skipped[] = []
    for (let i = 0; i < batch.length; i += CHUNK) {
      const res = await uploadBatch(id, batch.slice(i, i + CHUNK))
      acc.push(...res.accepted)
      rej.push(...res.rejected.map((r) => ({ name: r.name, reason: r.reason })))
      setSent(Math.min(i + CHUNK, batch.length))
    }
    setAccepted((p) => [...p, ...acc])
    setRejected((p) => [...p, ...rej])
  }

  async function start() {
    setBusy(true)
    setError('')
    setSent(0)
    try {
      await api('/api/auth/csrf/')
      await send(files)
      setFiles([])
      setConsent(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setBusy(false)
    }
  }

  async function retryUpload(name: string) {
    const f = kept.current.get(name)
    if (!f) return toast('Choose that file again to retry it.', 'bad')
    setRetrying(name)
    try {
      await api('/api/auth/csrf/')
      setRejected((p) => p.filter((r) => r.name !== name))
      await send([f])
    } catch (e) {
      setRejected((p) => [...p, { name, reason: e instanceof Error ? e.message : 'Upload failed.' }])
    } finally {
      setRetrying(null)
    }
  }

  const items = status.data?.items ?? []
  const looks = items.map(look)
  const done = looks.filter((l) => l.tone !== 'busy').length
  const total = accepted.length
  const pct = total ? Math.round((done / total) * 100) : 0
  const counts = {
    ok: looks.filter((l) => l.tone === 'ok').length,
    warn: looks.filter((l) => l.tone === 'warn' || l.tone === 'info').length,
    bad: looks.filter((l) => l.tone === 'bad').length + rejected.length,
  }
  const finished = total > 0 && !status.data?.in_progress && done === total

  return (
    <div className="space-y-6">
      <div
        data-drag={drag}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files) }}
        className={cn('dash-border rounded-card px-6 py-14 text-center transition-colors duration-(--dur-fast) sm:py-16', drag ? 'bg-surface-1' : 'bg-surface-panel')}
      >
        <span className={cn('mx-auto grid size-14 place-items-center rounded-pill border transition-colors duration-(--dur-fast)', drag ? 'border-signal text-signal' : 'bg-surface-1 text-text-2')}>
          <FileUp className="size-6" aria-hidden />
        </span>
        <p className="mt-4 text-h2">{drag ? 'Drop to add' : 'Drop PDF or DOCX CVs here'}</p>
        <p className="mx-auto mt-1 max-w-md text-small text-text-2">Up to 500 files, 5 MB each. Scanned PDFs are accepted but flagged for manual review.</p>
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          aria-label="Choose CV files"
          onChange={(e) => { if (e.target.files) add(e.target.files); e.target.value = '' }}
        />
        <Button variant="secondary" className="mt-5" onClick={() => input.current?.click()}>Choose files</Button>
      </div>

      {skipped.length > 0 && (
        <ul className="space-y-1.5 rounded-card border bg-surface-1 p-4 text-small" aria-label="Skipped files">
          {skipped.map((s, i) => (
            <li key={i} className="flex items-start gap-2">
              <StatusChip tone="warn">Skipped</StatusChip>
              <span className="min-w-0 truncate"><strong className="font-medium">{s.name}</strong> <span className="text-text-2">{s.reason}</span></span>
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <section className="surface-card space-y-4 rounded-card border p-5">
          <p className="text-body font-medium"><span className="tnum">{files.length}</span> file{files.length > 1 ? 's' : ''} ready</p>
          <ul className="max-h-56 divide-y overflow-auto rounded-input border bg-surface-panel text-small">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-3 px-3 py-2">
                <span className="min-w-0 flex-1 truncate">{f.name}</span>
                <span className="tnum shrink-0 text-text-2">{size(f.size)}</span>
                <Button variant="ghost" size="icon-xs" aria-label={`Remove ${f.name}`} disabled={busy} onClick={() => setFiles((p) => p.filter((_, n) => n !== i))}><X /></Button>
              </li>
            ))}
          </ul>
          <label className="flex items-start gap-3 rounded-input border bg-surface-panel p-3.5 text-small">
            <input type="checkbox" className="mt-0.5 size-4 accent-[var(--accent)]" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              <span className="flex items-center gap-1.5 font-medium"><ShieldCheck className="size-4" aria-hidden /> Consent is on record</span>
              <span className="text-text-2">These candidates have agreed to their CV being used for this hiring process only (DPDP Act 2023). A consent entry is recorded for each one, on their behalf.</span>
            </span>
          </label>
          {error && <p role="alert" className="text-small text-bad">{error}</p>}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={start} loading={busy} disabled={!consent} disabledReason="Tick the consent box first">
              {busy ? `Uploading ${sent}/${files.length}` : `Upload ${files.length} file${files.length > 1 ? 's' : ''}`}
            </Button>
            <Button variant="ghost" onClick={() => setFiles([])} disabled={busy}>Clear</Button>
          </div>
        </section>
      )}

      {(total > 0 || rejected.length > 0) && (
        <section className="space-y-4" aria-live="polite">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2>{finished ? 'Done' : 'Processing'}</h2>
              <p className="tnum text-small text-text-2">
                <CountUp value={done} /> of {total} processed · {counts.ok} scored · {counts.warn} flagged · {counts.bad} failed
              </p>
            </div>
            {finished && <Link to=".." className={buttonVariants({ size: 'sm' })}>View ranked list</Link>}
          </div>
          <FileProgress pct={pct} tone={finished ? 'ok' : 'busy'} label="Overall processing progress" />
          {status.isError && <p role="alert" className="text-small text-bad">Could not refresh progress. {status.error.message}</p>}
          <ul className="divide-y overflow-hidden rounded-card border bg-surface-1">
            {rejected.map((r, i) => (
              <li key={`r${i}`} className="space-y-2 p-4">
                <div className="flex items-center gap-3">
                  <span className="min-w-0 flex-1 truncate text-body">{r.name}</span>
                  <StatusChip tone="bad">Rejected</StatusChip>
                  <Button variant="secondary" size="sm" loading={retrying === r.name} disabled={!kept.current.has(r.name)} disabledReason="Choose the file again to retry it" onClick={() => retryUpload(r.name)}>
                    <RotateCw /> Retry
                  </Button>
                </div>
                <FileProgress pct={100} tone="bad" label={`${r.name}: rejected`} />
                <p className="text-small text-text-2">{r.reason}</p>
              </li>
            ))}
            {accepted.map((a) => {
              const item = items.find((i) => i.candidate_id === a.candidate_id)
              const l = look(item)
              return (
                <li key={a.candidate_id} className="space-y-2 p-4">
                  <div className="flex items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-body">{a.name}</p>
                      {item?.full_name && <p className="truncate text-small text-text-2">{item.full_name}</p>}
                    </div>
                    <StatusChip tone={l.chip}>{l.tone === 'busy' && <Spinner className="size-3" />}{l.label}</StatusChip>
                    {l.retry === 'rescore' && (
                      <Button variant="secondary" size="sm" loading={rescore.isPending && rescore.variables === a.candidate_id} onClick={() => rescore.mutate(a.candidate_id, { onSuccess: () => toast('Scoring queued.', 'info') })}>
                        <RotateCw /> Retry
                      </Button>
                    )}
                  </div>
                  <FileProgress pct={l.pct} tone={l.tone} label={`${a.name}: ${l.label}`} />
                  {l.detail && <p className="text-small text-text-2">{l.detail}</p>}
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </div>
  )
}
