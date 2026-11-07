import { CountUp } from '@/lib/motion'
import { cn } from '@/lib/utils'

export interface DistCounts { strong: number; possible: number; weak: number; review: number }
const SEGS = [
  { key: 'strong', label: 'Strong', bar: 'bg-ok', dot: 'bg-ok' },
  { key: 'possible', label: 'Possible', bar: 'bg-warn', dot: 'bg-warn' },
  { key: 'weak', label: 'Weak', bar: 'bg-bad', dot: 'bg-bad' },
  { key: 'review', label: 'Needs review', bar: 'bg-info', dot: 'bg-info' },
] as const

/** A tiny stacked bar of Strong / Possible / Weak / Needs review, with the counts spelled out so colour is never the only signal. */
export function DistBar({ counts, className }: { counts: DistCounts; className?: string }) {
  const total = counts.strong + counts.possible + counts.weak + counts.review
  return (
    <div className={cn('space-y-1.5', className)}>
      <div role="img" aria-label={SEGS.map((s) => `${counts[s.key]} ${s.label}`).join(', ')} className="flex h-[3px] gap-0.5 overflow-hidden rounded-pill bg-track opacity-70 transition-opacity duration-(--dur-fast) group-hover:opacity-100">
        {total > 0 && SEGS.map((s) => counts[s.key] > 0 && <span key={s.key} className={cn('h-full', s.bar)} style={{ flexGrow: counts[s.key] }} />)}
      </div>
      <p className="tnum flex flex-wrap gap-x-3 text-micro text-text-2">
        {SEGS.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1">
            <span aria-hidden className={cn('size-1.5 rounded-pill', s.dot)} />
            <CountUp value={counts[s.key]} /> {s.label.replace('Needs review', 'Review')}
          </span>
        ))}
      </p>
    </div>
  )
}
