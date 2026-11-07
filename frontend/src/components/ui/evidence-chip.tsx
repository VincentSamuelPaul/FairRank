import { Check } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

/** A compact chip: criterion + quote on one line. Click to expand into the full verified quote. */
export function EvidenceChip({ criterion, quote, unverified = false }: { criterion: string; quote: string; unverified?: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={() => setOpen((o) => !o)}
      className={cn(
        'group/chip min-w-0 text-left transition-[background-color,border-color] duration-(--dur-fast) hover:border-border-strong hover:bg-surface-2',
        open ? 'rounded-card border bg-surface-2 p-3 md:col-span-2' : 'flex w-full items-center gap-2 rounded-pill border bg-surface-panel py-1.5 pl-2.5 pr-3.5',
      )}
    >
      {open ? (
        <>
          <span className="flex items-center justify-between gap-3 text-micro uppercase text-text-2">
            <span className="truncate">{criterion}</span>
            <span className="inline-flex shrink-0 items-center gap-1.5">
              <Check className={cn('size-3', unverified ? 'text-warn' : 'text-ok')} aria-hidden />
              {unverified ? 'Unverified' : 'Verified in CV'}
            </span>
          </span>
          <span className="mt-1 block text-body text-text-1">“{quote}”</span>
        </>
      ) : (
        <>
          <Check className={cn('size-3.5 shrink-0', unverified ? 'text-warn' : 'text-ok')} aria-label={unverified ? 'Unverified' : 'Verified in CV'} />
          <span className="shrink-0 text-micro uppercase text-text-2">{criterion}</span>
          <span className="min-w-0 truncate text-small text-text-1">“{quote}”</span>
        </>
      )}
    </button>
  )
}
