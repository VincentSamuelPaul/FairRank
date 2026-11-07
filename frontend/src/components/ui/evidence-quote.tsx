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
  className?: string
}

/** A quote from the CV with the criterion it supports, or an honest "No evidence found". Never shows an unverified quote. */
export function EvidenceQuote({ criterion, quote, status, unverified = false, clamp = false, onSelect, active = false, showCriterion = true, className }: Props) {
  if (status === 'no_evidence' || !quote) {
    return (
      <div className={cn('rounded-input border border-dashed px-3 py-2', className)}>
        <p className="text-micro uppercase text-text-2">{criterion}</p>
        <p className="text-small text-text-3">No evidence found</p>
      </div>
    )
  }
  const text = <>“{quote}”</>
  return (
    <figure className={cn('border-l-2 pl-3', active ? 'border-accent' : 'border-border-strong', className)}>
      <figcaption className="flex items-center justify-between gap-3 text-micro uppercase text-text-2">
        {showCriterion && <span className="truncate">{criterion}</span>}
        <span className="inline-flex shrink-0 items-center gap-1.5">
          <span aria-hidden className={cn('size-1.5 rounded-pill', unverified ? 'bg-warn' : 'bg-ok')} />
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
