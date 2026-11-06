import { CheckCircle2, FileUp, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { BandPill } from '@/components/score'
import { Spinner } from '@/components/states'
import { Button, buttonVariants } from '@/components/ui/button'
import { api } from '@/lib/api'
import { uploadBatch, useUploadStatus } from '@/lib/queries'
import type { UploadItem } from '@/lib/types'
import { cn } from '@/lib/utils'

const MAX_BYTES = 5 * 1024 * 1024
const CHUNK = 25

interface Skipped {
  name: string
  reason: string
}

function describe(item: UploadItem): { label: string; tone: 'ok' | 'warn' | 'bad' | 'busy'; detail?: string } {
  if (item.cv_status === 'failed') return { label: 'Failed', tone: 'bad', detail: item.note }
  if (item.cv_status === 'needs_review') return { label: 'Needs manual review', tone: 'warn', detail: 'No readable text. It will not be scored.' }
  if (item.cv_status === 'queued') return { label: 'Parsing…', tone: 'busy' }
  const scoring = item.score_state === 'pending' || item.score_state === 'processing'
  if (item.cv_status === 'duplicate') return { label: scoring ? 'Duplicate · scoring…' : 'Duplicate', tone: 'warn', detail: item.note }
  if (scoring) return { label: 'Parsed · scoring…', tone: 'busy' }
  if (item.score_state === 'failed') return { label: 'Scoring failed, retry from the list', tone: 'bad' }
  return { label: 'Scored', tone: 'ok' }
}

export function UploadPage() {
  const { id = '' } = useParams()
  const input = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [skipped, setSkipped] = useState<Skipped[]>([])
  const [consent, setConsent] = useState(false)
  const [drag, setDrag] = useState(false)
  const [sent, setSent] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [accepted, setAccepted] = useState<{ candidate_id: string; name: string }[]>([])
  const [rejected, setRejected] = useState<Skipped[]>([])
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

  async function start() {
    setBusy(true)
    setError('')
    setSent(0)
    const acc: typeof accepted = []
    const rej: Skipped[] = []
    try {
      await api('/api/auth/csrf/')
      for (let i = 0; i < files.length; i += CHUNK) {
        const res = await uploadBatch(id, files.slice(i, i + CHUNK))
        acc.push(...res.accepted)
        rej.push(...res.rejected.map((r) => ({ name: r.name, reason: r.reason })))
        setSent(Math.min(i + CHUNK, files.length))
      }
      setFiles([])
      setConsent(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.')
    } finally {
      setAccepted((p) => [...p, ...acc])
      setRejected((p) => [...p, ...rej])
      setBusy(false)
    }
  }

  const items = status.data?.items ?? []
  const done = items.filter((i) => describe(i).tone !== 'busy').length
  const total = accepted.length
  const pct = total ? Math.round((done / total) * 100) : 0
  const counts = {
    ok: items.filter((i) => describe(i).tone === 'ok').length,
    warn: items.filter((i) => describe(i).tone === 'warn').length,
    bad: items.filter((i) => describe(i).tone === 'bad').length + rejected.length,
  }
  const finished = total > 0 && !status.data?.in_progress && done === total

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files) }}
        className={cn('rounded-xl border-2 border-dashed p-8 text-center transition-colors', drag ? 'border-primary bg-accent/50' : 'border-border')}
      >
        <FileUp className="mx-auto size-7 text-muted-foreground" aria-hidden />
        <p className="mt-2 font-medium">Drop PDF or DOCX CVs here</p>
        <p className="text-sm text-muted-foreground">Up to 500 files, 5 MB each. Scanned PDFs are accepted but flagged for manual review.</p>
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          aria-label="Choose CV files"
          onChange={(e) => { if (e.target.files) add(e.target.files); e.target.value = '' }}
        />
        <Button variant="outline" className="mt-4" onClick={() => input.current?.click()}>
          Choose files
        </Button>
      </div>

      {skipped.length > 0 && (
        <ul className="space-y-1 rounded-lg bg-muted/60 p-3 text-sm" aria-label="Skipped files">
          {skipped.map((s, i) => (
            <li key={i} className="flex gap-2">
              <TriangleAlert className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
              <span>
                <strong className="font-medium">{s.name}</strong> skipped: {s.reason}
              </span>
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <section className="space-y-4 rounded-xl border p-4">
          <p className="font-medium">
            {files.length} file{files.length > 1 ? 's' : ''} ready
          </p>
          <ul className="max-h-40 space-y-0.5 overflow-auto text-sm text-muted-foreground">
            {files.map((f, i) => (
              <li key={i} className="truncate">{f.name}</li>
            ))}
          </ul>
          <label className="flex items-start gap-2.5 rounded-lg bg-accent/50 p-3 text-sm">
            <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            <span>
              <span className="flex items-center gap-1.5 font-medium"><ShieldCheck className="size-4 text-primary" aria-hidden /> Consent is on record</span>
              These candidates have agreed to their CV being used for this hiring process only (DPDP Act 2023). A consent entry is recorded for each one, on their behalf.
            </span>
          </label>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <div className="flex items-center gap-3">
            <Button onClick={start} disabled={!consent || busy}>
              {busy ? <><Spinner /> Uploading {sent}/{files.length}</> : `Upload ${files.length} file${files.length > 1 ? 's' : ''}`}
            </Button>
            <Button variant="ghost" onClick={() => setFiles([])} disabled={busy}>Clear</Button>
          </div>
        </section>
      )}

      {(total > 0 || rejected.length > 0) && (
        <section className="space-y-3" aria-live="polite">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="font-medium">{finished ? 'Done' : 'Processing'}</h2>
              <p className="text-sm text-muted-foreground">
                {done} of {total} processed · {counts.ok} scored · {counts.warn} flagged · {counts.bad} failed
              </p>
            </div>
            {finished && <Link to=".." className={buttonVariants({ size: 'sm' })}>View ranked list</Link>}
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Processing progress">
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
          </div>
          {status.isError && <p role="alert" className="text-sm text-destructive">Could not refresh progress. {status.error.message}</p>}
          <ul className="divide-y rounded-xl border">
            {rejected.map((r, i) => (
              <li key={`r${i}`} className="flex items-start justify-between gap-3 p-3 text-sm">
                <span className="truncate">{r.name}</span>
                <span className="shrink-0 text-destructive">Rejected: {r.reason}</span>
              </li>
            ))}
            {accepted.map((a) => {
              const item = items.find((i) => i.candidate_id === a.candidate_id)
              const d = item ? describe(item) : { label: 'Queued', tone: 'busy' as const }
              return (
                <li key={a.candidate_id} className="flex items-start justify-between gap-3 p-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate">{a.name}</p>
                    {item?.full_name && <p className="truncate text-xs text-muted-foreground">{item.full_name}</p>}
                    {d.detail && <p className="text-xs text-muted-foreground">{d.detail}</p>}
                  </div>
                  <span className={cn('flex shrink-0 items-center gap-1.5 text-right', d.tone === 'bad' && 'text-destructive', d.tone === 'busy' && 'text-muted-foreground')}>
                    {d.tone === 'busy' && <Spinner />}
                    {d.tone === 'ok' && <CheckCircle2 className="size-4 text-primary" aria-hidden />}
                    {d.tone === 'warn' && <TriangleAlert className="size-4" aria-hidden />}
                    {d.label}
                    {d.tone === 'ok' && item?.band && <BandPill band={item.band} />}
                  </span>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </div>
  )
}
