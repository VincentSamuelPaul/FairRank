import { AlertTriangle, CircleHelp, ScanLine } from 'lucide-react'
import type { Band, ScoreState } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Spinner } from '@/components/states'
import { useCountUp } from '@/lib/motion'

/** Band from a weighted total (A2). The server sends the band; this is only the fallback. */
export const bandFor = (v: number): Band => (v >= 75 ? 'strong' : v >= 50 ? 'possible' : 'weak')

const WORD: Record<Band, string> = { strong: 'Strong', possible: 'Possible', weak: 'Weak' }
const STROKE: Record<Band, string> = { strong: 'stroke-ok', possible: 'stroke-warn', weak: 'stroke-bad' }
const GLOW: Record<Band, string> = { strong: '[--band:var(--ok)]', possible: '[--band:var(--warn)]', weak: '[--band:var(--bad)]' }
const TEXT: Record<Band, string> = { strong: 'text-ok', possible: 'text-warn', weak: 'text-bad' }
const SIZE = { sm: 'size-11 text-small', md: 'size-14 text-body', lg: 'size-24 text-h1' } as const

const NO_SCORE: Record<string, { icon: React.ReactNode; label: string; tone?: string }> = {
  needs_manual_review: { icon: <ScanLine className="size-1/2" />, label: 'Needs manual review' },
  failed: { icon: <AlertTriangle className="size-1/2" />, label: 'Scoring failed', tone: 'text-bad' },
  cv_failed: { icon: <AlertTriangle className="size-1/2" />, label: 'File unreadable', tone: 'text-bad' },
  processing: { icon: <Spinner className="size-1/2" />, label: 'Processing' },
  pending: { icon: <Spinner className="size-1/2" />, label: 'Scoring' },
  no_scorecard: { icon: <CircleHelp className="size-1/2" />, label: 'No scorecard yet' },
}

interface Props {
  value?: number | null
  band?: Band | null
  state?: ScoreState
  size?: keyof typeof SIZE
  /** Word under the ring instead of beside it (ranked list left column). */
  stacked?: boolean
  /** Word under the ring from the md breakpoint up, beside it on a phone (ranked rows). */
  stackedMd?: boolean
  /** Soft glow behind the ring in the band colour (12%, 24px blur). */
  glow?: boolean
  /** Fill animation length in ms (default 400). The login demo uses 900. */
  ms?: number
  className?: string
}

/**
 * 0 to 100 with the number centred and the band word beside it, so colour is never the only signal.
 * Without a score it shows a dashed ring and the reason: never a made-up number.
 */
export function ScoreRing({ value = null, band = null, state = 'scored', size = 'md', stacked = false, stackedMd = false, glow = false, ms = 400, className }: Props) {
  const shown = useCountUp(Math.round(value ?? 0), ms)
  const scored = state === 'scored' && value !== null
  const layout = cn('inline-flex items-center gap-3', stacked && 'flex-col gap-1.5 text-center', stackedMd && 'md:flex-col md:gap-1.5 md:text-center', className)
  if (!scored) {
    const s = NO_SCORE[state] ?? NO_SCORE.pending
    return (
      <span className={layout} role="img" aria-label={s.label}>
        <span className={cn('grid shrink-0 place-items-center rounded-pill border-2 border-dashed border-border-strong text-text-2', SIZE[size], s.tone)} aria-hidden>
          {s.icon}
        </span>
        <span className={cn('text-small font-medium', s.tone ?? 'text-text-2', stacked && 'max-w-24 leading-tight')}>{s.label}</span>
      </span>
    )
  }
  const v = Math.max(0, Math.min(100, value))
  const b = band ?? bandFor(v)
  const r = 16
  return (
    <span className={layout} role="img" aria-label={`Score ${Math.round(v)} out of 100, ${WORD[b]}`}>
      <span className={cn('relative grid shrink-0 place-items-center rounded-pill', SIZE[size], glow && cn(GLOW[b], 'shadow-[0_0_var(--glow-blur)_calc(var(--glow-blur)/4)_color-mix(in_srgb,var(--band)_12%,transparent)]'))}>
        <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90" aria-hidden>
          <circle cx="18" cy="18" r={r} fill="none" strokeWidth="3" className="stroke-border" />
          <circle cx="18" cy="18" r={r} fill="none" strokeWidth="3" strokeLinecap="round" pathLength={100} strokeDasharray={`${v} 100`} style={{ '--v': v, '--ms': `${ms}ms` } as React.CSSProperties} className={cn(STROKE[b], 'ring-fill')} />
        </svg>
        <span className="tnum relative font-medium leading-none">{shown}</span>
      </span>
      <span className={cn('text-small font-medium', TEXT[b])}>{WORD[b]}</span>
    </span>
  )
}
