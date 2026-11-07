import { cn } from '@/lib/utils'

/** Two-letter tile for a client. Neutral on purpose: it identifies, it does not decorate. */
export function Monogram({ name, className }: { name: string; className?: string }) {
  const letters = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('')
  return (
    <span aria-hidden className={cn('grid size-10 shrink-0 place-items-center rounded-input border bg-surface-2 text-small font-medium text-text-1', className)}>
      {letters || '?'}
    </span>
  )
}
