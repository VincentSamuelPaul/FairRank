import { useId } from 'react'
import { cn } from '@/lib/utils'

/** CSS-only tooltip that also opens on keyboard focus. Wrap a disabled control so people learn why it is disabled. */
export function Tooltip({ content, children, className }: { content: React.ReactNode; children: React.ReactNode; className?: string }) {
  const id = useId()
  return (
    <span tabIndex={0} aria-describedby={id} className={cn('group/tip relative inline-flex rounded-pill', className)}>
      {children}
      <span
        role="tooltip"
        id={id}
        className="pointer-events-none absolute bottom-full right-0 z-30 mb-2 w-max max-w-64 rounded-input border bg-surface-2 px-3 py-2 text-left text-small text-text-1 opacity-0 shadow-float transition-opacity duration-(--dur-fast) group-hover/tip:opacity-100 group-focus/tip:opacity-100 group-focus-within/tip:opacity-100"
      >
        {content}
      </span>
    </span>
  )
}
