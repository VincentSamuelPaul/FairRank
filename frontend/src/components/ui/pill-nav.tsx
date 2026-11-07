import { cn } from '@/lib/utils'

export interface PillItem {
  label: string
  onClick: () => void
  active?: boolean
}

/** SHOWCASE ONLY. A glass pill of text buttons. Every item must do something. */
export function PillNav({ items, label = 'Main', className }: { items: PillItem[]; label?: string; className?: string }) {
  return (
    <nav aria-label={label} className={cn('inline-flex items-center gap-1 rounded-pill border bg-glass p-1 backdrop-blur-(--blur-glass)', className)}>
      {items.map((i) => (
        <button
          key={i.label}
          type="button"
          onClick={i.onClick}
          aria-current={i.active ? 'true' : undefined}
          className={cn(
            'inline-flex h-9 items-center rounded-pill px-3.5 text-small transition-colors duration-(--dur-fast) sm:px-4',
            i.active ? 'bg-glass-strong text-text-1' : 'text-text-2 hover:text-text-1',
          )}
        >
          {i.label}
        </button>
      ))}
    </nav>
  )
}
