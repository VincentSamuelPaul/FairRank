import { cn } from '@/lib/utils'

interface Props {
  criterion: string
  quote?: string
  status: 'verified' | 'no_evidence'
  /** Low confidence: shown, but flagged. */
  unverified?: boolean
  /** Collapsed: 1 or 2 lines. */
  clamp?: boolean | 2
  /** Click the quote to scroll the CV text to its highlighted match. */
  onSelect?: () => void
  active?: boolean
  /** Hide the criterion label when the surrounding row already shows it. */
  showCriterion?: boolean
  /** Reveal after `delay` ms and draw the Verified tick (login demo). */
  reveal?: number
  className?: string
}

/** A quote from the CV with the criterion it supports, or an honest "No evidence found". Never shows an unverified quote. */
export function EvidenceQuote({ criterion, quote, status, unverified = false, clamp = false, onSelect, active = false, showCriterion = true, reveal, className }: Props) {
  const stage = reveal === undefined ? undefined : ({ '--d': `${reveal}ms` } as React.CSSProperties)
  if (status === 'no_evidence' || !quote) {
    return (
      <div style={stage} className={cn('rounded-input border border-dashed px-3 py-2', reveal !== undefined && 'proof-in', className)}>
        <p className="text-micro uppercase text-text-2">{criterion}</p>
        <p className="text-small text-text-2">No evidence found</p>
      </div>
    )
  }
  const text = <>“{quote}”</>
  return (
    <figure style={stage} className={cn('border-l-2 pl-3', active ? 'border-accent' : 'border-border-strong', reveal !== undefined && 'proof-in', className)}>
      <figcaption className="flex items-center justify-between gap-3 text-micro uppercase text-text-2">
        {showCriterion && <span className="truncate">{criterion}</span>}
        <span className="inline-flex shrink-0 items-center gap-1.5">
          {reveal !== undefined && !unverified ? (
            <svg aria-hidden viewBox="0 0 12 12" className="tick size-3 text-ok" style={{ '--d': `${reveal + 250}ms` } as React.CSSProperties}>
              <path d="M2 6.5 5 9.5 10 3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" pathLength={1} />
            </svg>
          ) : (
            <span aria-hidden className={cn('size-1.5 rounded-pill', unverified ? 'bg-warn' : 'bg-ok')} />
          )}
          {unverified ? 'Unverified' : 'Verified in CV'}
        </span>
      </figcaption>
      <blockquote className={cn('text-body text-text-1', clamp === 2 ? 'line-clamp-2' : clamp && 'line-clamp-1')}>
        {onSelect ? (
          <button type="button" onClick={onSelect} className="text-left hover:underline">
            {text}
          </button>
        ) : (
          text
        )}
      </blockquote>
    </figure>
  )
}
