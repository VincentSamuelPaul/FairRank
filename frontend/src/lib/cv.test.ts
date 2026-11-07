import { describe, expect, it } from 'vitest'
import { evidenceRanges, locate, maskRanges, mergeSpans, orderCriteria, segment, summarise } from '@/lib/cv'
import type { CriterionScore } from '@/lib/types'

const TEXT = ['Ritika Bansal', 'Senior Java Developer', 'Email: ritika.bansal@example.com', 'Phone: +91 90000 00001', '', '', 'SKILLS', 'Java, Spring Boot, Kafka', 'EXPERIENCE', 'Led a team of 5', 'Built and maintained 12 Spring Boot microservices', 'Gender: Female', 'Date of Birth: 1 September 1988'].join('\n')
const crit = (id: number, quote: string, over: Partial<CriterionScore> = {}): CriterionScore => {
  const i = TEXT.indexOf(quote)
  return { criterion_id: id, name: `C${id}`, weight: 3, is_must_have: true, points: 90, confidence: 1, unverified: false, evidence_status: 'verified', quote, rationale: '', span: i >= 0 ? [i, i + quote.length] : null, ...over }
}

describe('highlights', () => {
  it('cover exactly the quoted text, never the whole line', () => {
    const q = 'Spring Boot microservices'
    const [r] = evidenceRanges(TEXT, [crit(1, q)])
    expect(TEXT.slice(r.start, r.end)).toBe(q)
    const line = 'Built and maintained 12 Spring Boot microservices'
    expect(TEXT.slice(r.start, r.end)).not.toBe(line)
  })

  it('ignore criteria without verified evidence', () => {
    expect(evidenceRanges(TEXT, [crit(1, 'Kafka', { evidence_status: 'no_evidence' })])).toEqual([])
  })

  it('merge overlapping and adjacent spans into one that lists both criteria', () => {
    const at = (q: string) => TEXT.lastIndexOf(q)
    const spans = [
      { id: 1, start: at('Spring Boot microservices'), end: at('Spring Boot microservices') + 'Spring Boot microservices'.length },
      { id: 2, start: at('Boot microservices'), end: at('Boot microservices') + 'Boot microservices'.length },
    ]
    const merged = mergeSpans(TEXT, spans)
    expect(merged).toHaveLength(1)
    expect(merged[0].ids).toEqual([1, 2])
    expect(TEXT.slice(merged[0].start, merged[0].end)).toBe('Spring Boot microservices')
    expect(mergeSpans('foo bar', [{ id: 1, start: 0, end: 3 }, { id: 2, start: 4, end: 7 }])).toHaveLength(1)
    // quotes on different lines stay separate so each keeps its own number
    expect(mergeSpans('foo\nbar', [{ id: 1, start: 0, end: 3 }, { id: 2, start: 4, end: 7 }])).toHaveLength(2)
    expect(mergeSpans('foo, bar', [{ id: 1, start: 0, end: 3 }, { id: 2, start: 5, end: 8 }])).toHaveLength(2)
  })

  it('segment keeps every character exactly once', () => {
    const ranges = evidenceRanges(TEXT, [crit(1, 'Kafka'), crit(2, 'Led a team of 5')])
    expect(segment(TEXT, ranges).map((p) => TEXT.slice(p.start, p.end)).join('')).toBe(TEXT)
  })
})

describe('locate', () => {
  it('names the section and the line within it', () => {
    expect(locate(TEXT, TEXT.indexOf('Kafka'))).toBe('Skills, line 1')
    expect(locate(TEXT, TEXT.indexOf('Built and'))).toBe('Experience, line 2')
  })
})

describe('blind view mask', () => {
  it('hides name, email, phone, gender and date of birth, and nothing else', () => {
    const hidden = maskRanges(TEXT, { name: 'Ritika Bansal', email: 'ritika.bansal@example.com', phone: '+91 90000 00001' }).map((r) => TEXT.slice(r.start, r.end))
    expect(hidden.join('|')).toContain('Ritika Bansal')
    expect(hidden).toContain('ritika.bansal@example.com')
    expect(hidden).toContain('+91 90000 00001')
    expect(hidden).toContain('Female')
    expect(hidden).toContain('1 September 1988')
    expect(hidden.join('|')).not.toContain('Spring Boot')
  })
  it('skips values that are not available', () => {
    expect(maskRanges('Java developer', {})).toEqual([])
  })
})

describe('ordering and summary', () => {
  const cs = [crit(1, 'Kafka', { points: 95 }), crit(2, 'Java', { evidence_status: 'no_evidence', quote: '', span: null, points: 0 }), crit(3, 'Led a team of 5', { is_must_have: false, points: 40 })]
  it('lists rows that need a look first within each group', () => {
    const o = orderCriteria(cs)
    expect(o.must.map((c) => c.criterion_id)).toEqual([2, 1])
    expect(o.all.map((c) => c.criterion_id)).toEqual([2, 1, 3])
  })
  it('says how many must-haves are met and what is short', () => {
    expect(summarise(cs)).toBe('Meets 1 of 2 must-haves. Short on C2.')
  })
})
