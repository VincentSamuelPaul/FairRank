import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'
import type { CandidateDetail } from '@/lib/types'

const ID = '11111111-1111-1111-1111-111111111111'
const TEXT = 'Ritika Bansal\nSenior Java Developer\nEmail: r@example.com\n\n\nSKILLS\nJava, Spring Boot, Kafka\nEXPERIENCE\nBuilt and maintained 12 Spring Boot microservices\nNotice Period: 60 days'
const span = (q: string): [number, number] => [TEXT.indexOf(q), TEXT.indexOf(q) + q.length]

const detail = (over: Partial<CandidateDetail> = {}): CandidateDetail => ({
  id: ID, external_id: 'CND-1', full_name: 'Ritika Bansal', email: 'r@example.com', phone: '', current_role: 'Senior Java Developer', experience_years: 6.5, notice_days: 60, location: 'Noida', skills: ['Java'],
  stage: 'screened', cv_status: 'parsed', cv_note: '', original_name: 'cv.pdf', duplicate_of: null, viewed: true, submitted: false, created_at: '2026-11-06T00:00:00Z',
  next_action: { code: 'submit', label: 'Submit' }, raw_text: TEXT, cv_file_url: null, cv_file_kind: null,
  requisition: { id: 'R1', title: 'Senior Java Developer', client: 'Northwind' }, consent: [], view_log: { total: 1, recent: [] }, stage_events: [], allowed_moves: [], can_submit: true, submission: null,
  score: {
    state: 'scored', total: 82, band: 'strong', scorecard_version: 1, missing_must_haves: [], model: 'test',
    criteria: [
      { criterion_id: 1, name: 'Spring Boot', weight: 3, is_must_have: true, points: 90, confidence: 1, unverified: false, evidence_status: 'verified', quote: 'Built and maintained 12 Spring Boot microservices', rationale: 'Specific experience.', span: span('Built and maintained 12 Spring Boot microservices') },
      { criterion_id: 2, name: 'Kafka', weight: 3, is_must_have: true, points: 0, confidence: 1, unverified: false, evidence_status: 'no_evidence', quote: '', rationale: '', span: null },
      { criterion_id: 3, name: 'Notice period', weight: 1, is_must_have: false, points: 100, confidence: 1, unverified: false, evidence_status: 'verified', quote: 'Notice Period: 60 days', rationale: 'Meets it.', span: span('Notice Period: 60 days') },
    ],
  },
  ...over,
})

function setup(c: CandidateDetail) {
  const routes: Record<string, unknown> = { '/api/auth/me/': { id: 1, email: 'u@x.example', full_name: 'Asha', role: 'recruiter', client_org: null }, [`/api/candidates/${ID}/`]: c }
  vi.stubGlobal('fetch', vi.fn(async (url: string) => (url in routes ? new Response(JSON.stringify(routes[url]), { status: 200 }) : new Response('{}', { status: 403 }))))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/candidates/${ID}`]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('candidate page', () => {
  it('highlights exactly the verified quote spans, nothing more', async () => {
    setup(detail())
    await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    const marks = [...document.querySelectorAll('mark.cv-mark')].map((m) => m.textContent?.replace(/\d+$/, ''))
    expect(marks).toEqual(['Built and maintained 12 Spring Boot microservices', 'Notice Period: 60 days'])
    // the skills line contains "Spring Boot" but is not a quote, so it is not highlighted
    expect(document.querySelector('mark')?.textContent).not.toContain('Skills')
  })

  it('shows only the meta fields that exist and never an em dash', async () => {
    setup(detail({ experience_years: null, notice_days: null, location: '', current_role: '' }))
    const h = await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    const header = h.closest('header')!
    expect(header.textContent).not.toMatch(/[—–]/)
    expect(within(header).queryByText(/yrs|Notice/)).toBeNull()
    await userEvent.click(screen.getByRole('tab', { name: 'Profile' }))
    expect(screen.getAllByText('Not stated').length).toBeGreaterThan(2)
  })

  it('keeps Submit disabled until the CV was opened, then enables it', async () => {
    const view = setup(detail({ viewed: false, can_submit: false }))
    await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    // the header pill and the phone bar are both in the DOM (CSS shows one); every one of them is disabled
    const off = screen.getAllByRole('button', { name: /Submit to client/ })
    expect(off.length).toBeGreaterThan(0)
    off.forEach((b) => expect(b).toBeDisabled())
    expect(screen.getAllByRole('tooltip')[0]).toHaveTextContent('Open the CV first')
    view.unmount()
    setup(detail({ viewed: true, can_submit: true }))
    await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    screen.getAllByRole('button', { name: /Submit to client/ }).forEach((b) => expect(b).toBeEnabled())
  })

  it('lists criteria that need a look first and expands one at a time', async () => {
    setup(detail())
    await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    const rows = screen.getAllByRole('button', { expanded: false }).filter((b) => b.closest('li[id^=crit-]'))
    expect(rows[0]).toHaveTextContent('Kafka') // no evidence, flagged "Check", first within Must-have
    expect(rows[0]).toHaveTextContent('Check')
    await userEvent.click(rows[0])
    expect(screen.getByText(/No evidence found in this CV/)).toBeInTheDocument()
    await userEvent.click(rows[1])
    expect(screen.queryByText(/No evidence found in this CV/)).toBeNull()
    expect(screen.getByText('“Built and maintained 12 Spring Boot microservices”')).toBeInTheDocument()
  })

  it('masks identity in Blind view without putting the values in the DOM', async () => {
    setup(detail())
    await screen.findByRole('heading', { level: 1, name: 'Ritika Bansal' })
    await userEvent.click(screen.getByRole('button', { name: 'Blind view' }))
    const sheet = document.querySelector('.cv-sheet')!
    expect(sheet.textContent).not.toContain('Ritika')
    expect(sheet.textContent).not.toContain('r@example.com')
    expect(sheet.querySelectorAll('.cv-redact').length).toBeGreaterThan(1)
  })
})
