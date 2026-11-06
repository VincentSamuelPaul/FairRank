import type { Stage } from '@/lib/types'

export const STAGES: { key: Stage; label: string }[] = [
  { key: 'sourced', label: 'Sourced' },
  { key: 'screened', label: 'Screened' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'shortlisted', label: 'Shortlisted' },
  { key: 'interview', label: 'Interview' },
  { key: 'offered', label: 'Offered' },
  { key: 'joined', label: 'Joined' },
  { key: 'rejected', label: 'Rejected' },
]
export const stageLabel = (s: Stage) => STAGES.find((x) => x.key === s)?.label ?? s

export const years = (n: number | null) => (n === null ? '—' : `${n % 1 === 0 ? n : n.toFixed(1)} yrs`)
export const notice = (d: number | null) => (d === null ? '—' : d === 0 ? 'Immediate' : `${d} days`)

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })
export const dateOnly = (iso: string) => new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

export const lakhs = (inr: number | null) => (inr === null ? '' : `${(inr / 100000).toFixed(inr % 100000 === 0 ? 0 : 1)} LPA`)
