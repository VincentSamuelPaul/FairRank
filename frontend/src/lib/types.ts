export type Band = 'strong' | 'possible' | 'weak'
export type ScoreState =
  | 'scored'
  | 'needs_manual_review'
  | 'failed'
  | 'cv_failed'
  | 'processing'
  | 'pending'
  | 'no_scorecard'
export type Stage =
  | 'sourced'
  | 'screened'
  | 'submitted'
  | 'shortlisted'
  | 'interview'
  | 'offered'
  | 'joined'
  | 'rejected'

export interface CriterionScore {
  criterion_id: number
  name: string
  weight: number
  is_must_have: boolean
  points: number
  confidence: number
  unverified: boolean
  evidence_status: 'verified' | 'no_evidence'
  quote: string
  rationale: string
  span?: [number, number] | null
}

export interface ScorePayload {
  state: ScoreState
  total: number | null
  band: Band | null
  criteria: CriterionScore[]
  missing_must_haves: string[]
  scorecard_version: number | null
  model?: string
  error?: string
}

export interface NextAction {
  code: 'wait' | 'fix_file' | 'track' | 'retry' | 'open' | 'submit'
  label: string
}

export interface CandidateRow {
  id: string
  external_id: string
  full_name: string
  email: string
  phone: string
  current_role: string
  experience_years: number | null
  notice_days: number | null
  location: string
  skills: string[]
  stage: Stage
  cv_status: 'queued' | 'parsed' | 'needs_review' | 'duplicate' | 'failed' | 'none'
  cv_note: string
  original_name: string
  duplicate_of: { id: string; external_id: string; full_name: string; same_requisition: boolean } | null
  score: ScorePayload
  viewed: boolean
  submitted: boolean
  next_action: NextAction
  created_at: string
}

export interface Slot {
  id: number
  starts_at: string
  duration_minutes: number
  status: 'proposed' | 'confirmed' | 'declined'
  note: string
}

export interface Decision {
  decision: 'shortlist' | 'reject'
  reason: string
  at: string
}

export interface CandidateDetail extends CandidateRow {
  raw_text: string
  cv_file_url: string | null
  cv_file_kind: 'pdf' | 'docx' | null
  requisition: { id: string; title: string; client: string }
  consent: { source: string; purpose: string; recorded_at: string; recorded_by: string }[]
  view_log: { total: number; recent: { user: string; kind: string; at: string }[] }
  stage_events: { from: Stage; to: Stage; at: string; reason: string; by: string }[]
  allowed_moves: Stage[]
  can_submit: boolean
  submission: { submitted_at: string; note: string; decisions: Decision[]; slots: Slot[] } | null
}

export interface Criterion {
  id?: number
  name: string
  description: string
  weight: number
  is_must_have: boolean
}

export interface Scorecard {
  id: number
  version: number
  source: 'ai' | 'manual'
  created_at: string
  criteria: (Criterion & { id: number })[]
}

export interface Requisition {
  id: string
  title: string
  status: 'open' | 'closed'
  location: string
  client: { id: number; name: string }
  exp_min_years: number | null
  exp_max_years: number | null
  notice_max_days: number | null
  ctc_min: number | null
  ctc_max: number | null
  created_at: string
  scorecard_version: number | null
  jd_text?: string
  scorecard?: Scorecard | null
  counts?: { candidates: number; submitted: number }
}

export interface RankedList {
  requisition: Requisition
  scorecard: Scorecard | null
  counts: {
    total: number
    strong: number
    possible: number
    weak: number
    unscored: number
    needs_review: number
    failed: number
    processing: number
    duplicates: number
  }
  candidates: CandidateRow[]
}

export interface UploadItem {
  candidate_id: string
  name: string
  full_name: string
  cv_status: CandidateRow['cv_status']
  note: string
  score_state: ScoreState
  band: Band | null
  total: number | null
}

export interface PipelineColumn {
  stage: Stage
  label: string
  candidates: {
    id: string
    full_name: string
    external_id: string
    current_role: string
    score: number | null
    band: Band | null
    state: ScoreState
    allowed_moves: Stage[]
  }[]
}

export interface PipelineSummary {
  id: string
  title: string
  client: string
  status: string
  counts: Record<Stage, number>
  total: number
}

export interface ClientCard {
  id: string
  full_name: string
  current_role: string
  experience_years: number | null
  notice_days: number | null
  location: string
  skills: string[]
  stage: Stage
  contacts: { email: string; phone: string; masked: boolean }
  score: ScorePayload
  requisition: { id: string; title: string }
  submitted_at: string
  recruiter_note: string
  decision: Decision | null
  slots: Slot[]
  cv_text?: string
}

export interface PortalRequisition {
  id: string
  title: string
  location: string
  status: string
  submitted: number
  awaiting_decision: number
}

export interface AgreementReport {
  window_days: number
  generated_at: string
  overall: { requisitions: number; submitted: number; agreement_pct: number | null }
  requisitions: {
    requisition_id: string
    title: string
    client: string
    submitted: number
    in_ai_top_n: number
    agreement_pct: number | null
    disagreements: {
      type: 'recruiter_chose_lower_ranked' | 'ai_ranked_higher_not_submitted'
      candidate_id: string
      name: string
      external_id: string
      ai_rank: number | null
      score: number | null
      band: Band | null
    }[]
  }[]
  acceptance_by_band: { band: string; submitted: number; accepted: number; rejected: number; pending: number }[]
}
