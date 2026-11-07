import type { CriterionScore } from '@/lib/types'

/** Pure helpers behind the candidate page: highlight spans, sections, blind masking, summary. All display-only. */

export type RangeKind = 'evidence' | 'find' | 'findActive' | 'mask'
export interface Range {
  start: number
  end: number
  kind: RangeKind
  /** criterion ids for evidence ranges (several when adjacent quotes were merged) */
  ids?: number[]
}
export interface Piece {
  start: number
  end: number
  ranges: Range[]
}

/** Overlapping or adjacent (nothing but spaces between, on the same line) spans become one highlight that lists every criterion it carries. */
export function mergeSpans(text: string, spans: { id: number; start: number; end: number }[]): Range[] {
  const sorted = [...spans].filter((s) => s.end > s.start).sort((a, b) => a.start - b.start || a.end - b.end)
  const out: Range[] = []
  for (const s of sorted) {
    const last = out[out.length - 1]
    if (last && (s.start <= last.end || /^[ \t]*$/.test(text.slice(last.end, s.start)))) {
      last.end = Math.max(last.end, s.end)
      last.ids!.push(s.id)
    } else out.push({ start: s.start, end: s.end, kind: 'evidence', ids: [s.id] })
  }
  return out
}

/** Evidence ranges from verified criteria. Only the exact span of the quote is ever highlighted. */
export function evidenceRanges(text: string, criteria: CriterionScore[]): Range[] {
  return mergeSpans(
    text,
    criteria.filter((c) => c.evidence_status === 'verified' && c.span && c.span[1] > c.span[0]).map((c) => ({ id: c.criterion_id, start: c.span![0], end: c.span![1] })),
  )
}

/** Cut `text` at every range boundary; each piece knows which ranges cover it. */
export function segment(text: string, ranges: Range[]): Piece[] {
  const cuts = new Set<number>([0, text.length])
  for (const r of ranges) {
    cuts.add(Math.max(0, r.start))
    cuts.add(Math.min(text.length, r.end))
  }
  const pts = [...cuts].sort((a, b) => a - b)
  const out: Piece[] = []
  for (let i = 0; i < pts.length - 1; i++) {
    const [start, end] = [pts[i], pts[i + 1]]
    if (end > start) out.push({ start, end, ranges: ranges.filter((r) => r.start < end && r.end > start) })
  }
  return out
}

export interface Line {
  start: number
  end: number
  text: string
}
export const splitLines = (text: string): Line[] => {
  const lines: Line[] = []
  let at = 0
  for (const t of text.split('\n')) {
    lines.push({ start: at, end: at + t.length, text: t })
    at += t.length + 1
  }
  return lines
}

const HEADINGS = new Set(['summary', 'profile', 'objective', 'skills', 'technical skills', 'experience', 'work experience', 'employment', 'education', 'projects', 'certifications', 'achievements', 'languages', 'personal details', 'personal information', 'declaration', 'references'])
export function isHeading(line: string): boolean {
  const t = line.trim().replace(/:$/, '')
  if (t.length < 3 || t.length > 32) return false
  return HEADINGS.has(t.toLowerCase()) || /^[A-Z][A-Z &/]{2,31}$/.test(t)
}

/** "Experience, line 3": the nearest heading above `offset` and the line's number among the non-empty lines under it. */
export function locate(text: string, offset: number): string {
  let section: string | null = null
  let n = 0
  let overall = 0
  for (const l of splitLines(text)) {
    if (l.start > offset) break
    if (!l.text.trim()) continue
    overall++
    if (isHeading(l.text)) {
      section = l.text.trim().replace(/:$/, '')
      n = 0
    } else n++
  }
  const label = section ? section.charAt(0) + section.slice(1).toLowerCase() : null
  return label ? `${label}, line ${Math.max(n, 1)}` : `Line ${Math.max(overall, 1)}`
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Case-insensitive occurrences of `q` (for Find in CV). */
export function findRanges(text: string, q: string): Range[] {
  const needle = q.trim()
  if (needle.length < 2) return []
  const out: Range[] = []
  for (const m of text.matchAll(new RegExp(escape(needle), 'gi'))) out.push({ start: m.index!, end: m.index! + m[0].length, kind: 'find' })
  return out
}

/**
 * Display-only mask for Blind view: the candidate's name, email and phone (the values the parser extracted), plus the value on
 * Gender / Date of birth / Marital status / Age lines. Values that are not available are skipped.
 */
export function maskRanges(text: string, who: { name?: string; email?: string; phone?: string }): Range[] {
  const found: Range[] = []
  const add = (re: RegExp, group = 0) => {
    for (const m of text.matchAll(re)) {
      const s = m.index! + (group ? m[0].indexOf(m[group]) : 0)
      found.push({ start: s, end: s + (group ? m[group] : m[0]).length, kind: 'mask' })
    }
  }
  const name = who.name?.trim()
  if (name) {
    add(new RegExp(escape(name), 'gi'))
    for (const part of name.split(/\s+/).filter((p) => p.length >= 3)) add(new RegExp(`\\b${escape(part)}\\b`, 'gi'))
  }
  if (who.email?.trim()) add(new RegExp(escape(who.email.trim()), 'gi'))
  const digits = (who.phone ?? '').replace(/\D/g, '')
  if (digits.length >= 6) add(new RegExp(`\\+?${digits.split('').map(escape).join('[\\s\\-.()]*')}`, 'g'))
  add(/^[ \t]*(?:gender|sex|date of birth|dob|birth date|marital status|age|nationality)[ \t]*[:\-–][ \t]*(.+)$/gim, 1)
  // merge overlaps
  found.sort((a, b) => a.start - b.start || b.end - a.end)
  const out: Range[] = []
  for (const r of found) {
    const last = out[out.length - 1]
    if (last && r.start <= last.end) last.end = Math.max(last.end, r.end)
    else out.push({ ...r })
  }
  return out
}

/** CTC lines are not in the API payload; read them from the CV text for display only. */
export function ctcFromText(text: string, which: 'current' | 'expected'): string | null {
  const m = text.match(new RegExp(`${which}\\s+ctc\\s*[:\\-]\\s*([^\\n]+)`, 'i'))
  return m ? m[1].trim() : null
}

export const needsCheck = (c: CriterionScore) => c.evidence_status === 'no_evidence' || c.unverified || c.points < 50
export type Status = 'met' | 'partial' | 'none'
export const statusOf = (c: CriterionScore): Status => (c.evidence_status === 'no_evidence' ? 'none' : c.points >= 70 && !c.unverified ? 'met' : 'partial')

/** Must-haves then nice-to-haves; inside each, rows that need a look come first. The index here is the number shown on both panes. */
export function orderCriteria(criteria: CriterionScore[]): { must: CriterionScore[]; nice: CriterionScore[]; all: CriterionScore[] } {
  const rank = (a: CriterionScore, b: CriterionScore) => Number(needsCheck(b)) - Number(needsCheck(a))
  const must = criteria.filter((c) => c.is_must_have).sort(rank)
  const nice = criteria.filter((c) => !c.is_must_have).sort(rank)
  return { must, nice, all: [...must, ...nice] }
}

/** "Meets 3 of 4 must-haves. Short on years of experience." */
export function summarise(criteria: CriterionScore[]): string {
  const must = criteria.filter((c) => c.is_must_have)
  if (!must.length) return 'No must-haves on this scorecard.'
  const short = must.filter((c) => statusOf(c) !== 'met')
  const head = `Meets ${must.length - short.length} of ${must.length} must-haves.`
  if (!short.length) return head
  const names = short.slice(0, 2).map((c) => c.name)
  return `${head} Short on ${names.join(' and ')}${short.length > 2 ? ` and ${short.length - 2} more` : ''}.`
}
