import { CountUp } from '@/lib/motion'
import { cn } from '@/lib/utils'

export type BandKey = 'strong' | 'possible' | 'weak' | 'review'
const SEGS: { key: BandKey; label: string; hue: string }[] = [
  { key: 'strong', label: 'Strong', hue: '--ok' },
  { key: 'possible', label: 'Possible', hue: '--warn' },
  { key: 'weak', label: 'Weak', hue: '--bad' },
  { key: 'review', label: 'Needs review', hue: '--info' },
]

/** A segmented bar sized by how many CVs fall in each band. Each segment filters the list; click again to clear. */
export function BandBar({ counts, value, onChange }: { counts: Record<BandKey, number>; value: string; onChange: (v: BandKey | 'all') => void }) {
  return (
    <div role="group" aria-label="Filter by band" className="grid grid-cols-2 gap-1.5 sm:flex">
      {SEGS.map((s) => {
        const on = value === s.key
        return (
          <button
            key={s.key}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? 'all' : s.key)}
            style={{ '--h': `var(${s.hue})`, flexGrow: Math.max(counts[s.key], 1.2) } as React.CSSProperties}
            className={cn(
              'flex min-h-12 items-center justify-between gap-3 rounded-input border border-l-[3px] border-l-(--h) px-3.5 text-left transition-colors duration-(--dur-fast) sm:basis-0',
              on ? 'border-signal border-l-(--h) bg-surface-2 text-text-1 outline-1 outline-signal' : 'surface-card text-text-1 hover:bg-surface-2',
            )}
          >
            <span className="text-small font-medium">{s.label}</span>
            <span className="tnum text-h2 text-(--h)"><CountUp value={counts[s.key]} /></span>
          </button>
        )
      })}
    </div>
  )
}
