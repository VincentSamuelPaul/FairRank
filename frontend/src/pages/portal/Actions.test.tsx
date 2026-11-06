import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ClientCard } from '@/lib/types'
import { DecisionActions } from './Actions'

const card = (stage: ClientCard['stage']): ClientCard => ({
  id: 'c1', full_name: 'Jane Doe', current_role: 'Dev', experience_years: 5, notice_days: 30, location: 'Noida', skills: [],
  stage, contacts: { email: '', phone: '', masked: true },
  score: { state: 'scored', total: 80, band: 'strong', criteria: [], missing_must_haves: [], scorecard_version: 1 },
  requisition: { id: 'r', title: 'Java' }, submitted_at: '2026-11-06T00:00:00Z', recruiter_note: '', decision: null, slots: [],
})
const wrap = (ui: React.ReactNode) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)

afterEach(() => vi.unstubAllGlobals())

describe('client decisions', () => {
  it('requires a reason to reject and does not call the API without one', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    wrap(<DecisionActions card={card('submitted')} />)
    await userEvent.click(screen.getByRole('button', { name: /reject/i }))
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Reject' }))
    expect(await screen.findByText(/Tell the recruiter why/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('sends the reason when given', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(card('rejected')), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    wrap(<DecisionActions card={card('submitted')} />)
    await userEvent.click(screen.getByRole('button', { name: /reject/i }))
    await userEvent.type(screen.getByLabelText('Reason'), 'Needs more Kafka')
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Reject' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/portal/candidates/c1/decision/')
    expect(JSON.parse(init.body as string)).toEqual({ decision: 'reject', reason: 'Needs more Kafka' })
  })
  it('offers no decisions once a candidate is rejected', () => {
    wrap(<DecisionActions card={card('rejected')} />)
    expect(screen.queryByRole('button')).toBeNull()
  })
})
