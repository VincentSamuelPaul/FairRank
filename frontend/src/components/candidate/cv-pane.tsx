import { ChevronDown, ChevronUp, EyeOff, ExternalLink, ScanLine, Search, Minus, Plus } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { buttonVariants } from '@/components/ui/button'
import { evidenceRanges, findRanges, isHeading, maskRanges, segment, splitLines, type Range } from '@/lib/cv'
import { prefersReducedMotion } from '@/lib/motion'
import type { CandidateDetail } from '@/lib/types'
import { cn } from '@/lib/utils'

interface Props {
  c: CandidateDetail
  /** criterion id -> the number shown on both panes */
  numbers: Map<number, number>
  activeId: number | null
  /** bumps every time a criterion asks to be shown (hover, focus, click) */
  focusTick: number
  onSelect: (id: number) => void
  findRef: React.RefObject<HTMLInputElement | null>
  /** phone: the caption of the selected criterion, shown under the toolbar */
  caption?: React.ReactNode
}

const toolbarBtn = 'inline-flex size-9 items-center justify-center rounded-input text-text-2 transition-colors duration-(--dur-fast) hover:bg-surface-2 hover:text-text-1 disabled:opacity-40'

/** The CV as a light paper sheet. Highlights are the exact verified quote spans only; Blind view masks identity in the display. */
export function CvPane({ c, numbers, activeId, focusTick, onSelect, findRef, caption }: Props) {
  const text = c.raw_text
  const empty = text.trim().length === 0
  const [q, setQ] = useState('')
  const [at, setAt] = useState(0)
  const [size, setSize] = useState(15)
  const [blind, setBlind] = useState(false)
  const paper = useRef<HTMLDivElement>(null)

  const evidence = useMemo(() => evidenceRanges(text, c.score.criteria), [text, c.score.criteria])
  const found = useMemo(() => findRanges(text, q), [text, q])
  const masks = useMemo(() => (blind ? maskRanges(text, { name: c.full_name, email: c.email, phone: c.phone }) : []), [blind, text, c.full_name, c.email, c.phone])
  const idx = found.length ? ((at % found.length) + found.length) % found.length : 0
  const ranges: Range[] = useMemo(
    () => [...evidence, ...found.map((r, i) => (i === idx ? { ...r, kind: 'findActive' as const } : r)), ...masks],
    [evidence, found, idx, masks],
  )
  const lines = useMemo(() => splitLines(text), [text])

  // a criterion asked to be shown: scroll to its highlight (smooth unless reduced motion)
  useEffect(() => {
    if (!focusTick || activeId === null) return
    const el = paper.current?.querySelector(`[data-ids~="${activeId}"]`)
    el?.scrollIntoView({ block: 'center', behavior: prefersReducedMotion() ? 'auto' : 'smooth' })
  }, [focusTick, activeId])
  // moving between find matches scrolls to the active one
  useEffect(() => {
    if (found.length) paper.current?.querySelector('[data-find-active="true"]')?.scrollIntoView({ block: 'center', behavior: 'auto' })
  }, [idx, q, found.length])

  if (empty)
    return (
      <div className="m-4 flex flex-col items-center gap-3 rounded-card border border-dashed p-10 text-center lg:m-0">
        <ScanLine className="size-7 text-text-2" aria-hidden />
        <p className="text-h2">Needs manual review</p>
        <p className="max-w-sm text-small text-text-2">This file has no readable text (scanned or image-only), so it was not scored. Open the original and judge it yourself. It is not rejected or hidden.</p>
        {c.cv_file_url && (
          <a href={c.cv_file_url} target="_blank" rel="noreferrer" className={buttonVariants({ variant: 'secondary' })}>
            Open original {c.cv_file_kind?.toUpperCase()} <ExternalLink aria-hidden />
          </a>
        )}
      </div>
    )

  let blank = false
  const rendered = lines.map((l, li) => {
    if (!l.text.trim()) {
      if (blank || li === 0) return null // runs of blank lines collapse to one gap
      blank = true
      return <div key={li} aria-hidden className="h-2" />
    }
    blank = false
    const local = ranges.filter((r) => r.start < l.end && r.end > l.start).map((r) => ({ ...r, start: r.start - l.start, end: r.end - l.start }))
    const pieces = segment(l.text, local).map((p) => {
      const key = `${li}-${p.start}`
      const mask = p.ranges.some((r) => r.kind === 'mask')
      if (mask) return <span key={key} role="img" aria-label="Hidden" className="cv-redact" style={{ width: `${Math.max(2, p.end - p.start)}ch` }} />
      const ev = p.ranges.find((r) => r.kind === 'evidence')
      const f = p.ranges.find((r) => r.kind === 'find' || r.kind === 'findActive')
      const body = l.text.slice(p.start, p.end)
      if (!ev) return f ? <span key={key} className="cv-find" data-active={f.kind === 'findActive' || undefined}>{body}</span> : body
      const ids = ev.ids ?? []
      const origin = evidence.find((r) => r.start < l.start + p.end && r.end > l.start + p.start)!
      const endsHere = origin.end === l.start + p.end // the number sits after the last piece of the highlight
      const isActive = activeId !== null && ids.includes(activeId)
      return (
        <mark
          key={isActive ? `${key}-${focusTick}` : key}
          className={cn('cv-mark', isActive && focusTick > 0 && 'pulse')}
          data-ids={ids.join(' ')}
          data-active={isActive}
          data-find-active={f?.kind === 'findActive' || undefined}
          tabIndex={0}
          role="button"
          aria-label={`Evidence for ${ids.map((i) => `criterion ${numbers.get(i)}`).join(' and ')}. Select to see it in the analysis.`}
          onClick={() => onSelect(ids[0])}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onSelect(ids[0])
            }
          }}
        >
          {body}
          {endsHere && <sup className="cv-sup" aria-hidden>{ids.map((i) => numbers.get(i)).filter(Boolean).join('·')}</sup>}
        </mark>
      )
    })
    return isHeading(l.text) ? (
      <h3 key={li} className="cv-heading">{pieces}</h3>
    ) : (
      <p key={li}>{pieces}</p>
    )
  })

  const go = (d: number) => setAt((n) => n + d)
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="sticky top-0 z-10 space-y-2 border-b bg-ws/95 px-1 py-2 backdrop-blur-sm">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="relative min-w-40 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-3" aria-hidden />
            <input
              ref={findRef}
              type="search"
              aria-label="Find in CV"
              placeholder="Find in CV"
              value={q}
              onChange={(e) => { setQ(e.target.value); setAt(0) }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); go(e.shiftKey ? -1 : 1) }
                if (e.key === 'Escape') { setQ(''); e.currentTarget.blur() }
              }}
              className="h-9 w-full rounded-input border border-border-strong bg-surface-1 pl-9 pr-24 text-small text-text-1 outline-none placeholder:text-text-3 focus-visible:border-signal focus-visible:ring-3 focus-visible:ring-signal/25"
            />
            {q.trim().length >= 2 && (
              <span aria-live="polite" className="tnum absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-0.5 text-micro text-text-2">
                {found.length ? `${idx + 1}/${found.length}` : '0'}
                <button type="button" aria-label="Previous match" disabled={!found.length} onClick={() => go(-1)} className="grid size-6 place-items-center rounded-xs hover:bg-surface-2 disabled:opacity-40"><ChevronUp className="size-3.5" aria-hidden /></button>
                <button type="button" aria-label="Next match" disabled={!found.length} onClick={() => go(1)} className="grid size-6 place-items-center rounded-xs hover:bg-surface-2 disabled:opacity-40"><ChevronDown className="size-3.5" aria-hidden /></button>
              </span>
            )}
          </div>
          <div className="flex items-center gap-1" role="group" aria-label="Text size">
            <button type="button" aria-label="Smaller text" disabled={size <= 12} onClick={() => setSize((s) => s - 1)} className={toolbarBtn}><Minus className="size-4" aria-hidden /></button>
            <span aria-hidden className="tnum w-7 text-center text-micro text-text-2">{size}</span>
            <button type="button" aria-label="Larger text" disabled={size >= 20} onClick={() => setSize((s) => s + 1)} className={toolbarBtn}><Plus className="size-4" aria-hidden /></button>
          </div>
          <button
            type="button"
            aria-pressed={blind}
            onClick={() => setBlind((b) => !b)}
            className={cn('inline-flex h-9 items-center gap-1.5 rounded-pill border px-3 text-small transition-colors duration-(--dur-fast)', blind ? 'border-signal bg-surface-2 text-text-1' : 'border-border-strong text-text-2 hover:text-text-1')}
          >
            <EyeOff className="size-4" aria-hidden /> Blind view
          </button>
          {c.cv_file_url && (
            <a href={c.cv_file_url} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-1 text-small text-signal hover:underline">
              Open original {c.cv_file_kind?.toUpperCase()} <ExternalLink className="size-3.5" aria-hidden />
            </a>
          )}
        </div>
        {blind && <p role="status" className="text-micro text-text-2">Name, contact, gender, date of birth and marital status are masked here. Hidden from scoring too.</p>}
        {caption}
      </div>
      <div className="px-1 py-4 lg:px-0">
        <div ref={paper} className="cv-sheet mx-auto max-w-[70ch] px-5 py-8 leading-[1.7] sm:px-10 sm:py-10" style={{ fontSize: size }}>
          {rendered}
        </div>
      </div>
    </div>
  )
}
