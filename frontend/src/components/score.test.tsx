import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvidenceList, MaskedContacts, ScoreBadge } from '@/components/score'
import type { CriterionScore, ScorePayload } from '@/lib/types'

const crit = (over: Partial<CriterionScore>): CriterionScore => ({
  criterion_id: 1, name: 'Java', weight: 3, is_must_have: true, points: 90, confidence: 0.9, unverified: false,
  evidence_status: 'verified', quote: 'Built Spring Boot services', rationale: '', ...over,
})
const score = (over: Partial<ScorePayload>): ScorePayload => ({
  state: 'scored', total: 84.4, band: 'strong', criteria: [], missing_must_haves: [], scorecard_version: 1, ...over,
})

describe('ScoreBadge', () => {
  it('shows the score and band', () => {
    render(<ScoreBadge score={score({})} />)
    expect(screen.getByText('84')).toBeInTheDocument()
    expect(screen.getByText('Strong')).toBeInTheDocument()
  })
  it('never invents a number for a scanned CV', () => {
    render(<ScoreBadge score={score({ state: 'needs_manual_review', total: null, band: null })} />)
    expect(screen.getByText('Needs manual review')).toBeInTheDocument()
    expect(screen.queryByText(/^\d+$/)).toBeNull()
  })
  it('shows a retryable failure state', () => {
    render(<ScoreBadge score={score({ state: 'failed', total: null, band: null })} />)
    expect(screen.getByText('Scoring failed')).toBeInTheDocument()
  })
})

describe('EvidenceList', () => {
  it('shows verified quotes, "No evidence found" and the unverified flag', () => {
    render(
      <EvidenceList
        criteria={[
          crit({}),
          crit({ criterion_id: 2, name: 'Kafka', evidence_status: 'no_evidence', quote: '', points: 0 }),
          crit({ criterion_id: 3, name: 'AWS', unverified: true, confidence: 0.4, quote: 'Familiar with AWS' }),
        ]}
      />,
    )
    expect(screen.getByText(/Built Spring Boot services/)).toBeInTheDocument()
    expect(screen.getByText('No evidence found')).toBeInTheDocument()
    expect(screen.getByText(/Unverified · low confidence/)).toBeInTheDocument()
  })
})

describe('MaskedContacts', () => {
  it('explains masking before the interview stage', () => {
    render(<MaskedContacts contacts={{ email: 'j•••@e•••.com', phone: '•••• ••• •10', masked: true }} />)
    expect(screen.getByText('j•••@e•••.com')).toBeInTheDocument()
    expect(screen.getByText(/unlock when you reach the interview stage/)).toBeInTheDocument()
  })
})
