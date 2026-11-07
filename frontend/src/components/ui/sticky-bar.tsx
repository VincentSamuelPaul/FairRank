import { cn } from '@/lib/utils'

/** Phone-only bar pinned to the bottom for the page's primary action. Solid (workspace has no blur) and safe-area aware. */
export function StickyBar({ children, className, from = 'lg' }: { children: React.ReactNode; className?: string; from?: 'md' | 'lg' }) {
  return (
    <div className={cn('fixed inset-x-0 bottom-0 z-30 border-t bg-ws px-(--gutter) pt-3 pb-[calc(0.75rem+var(--safe-bottom))]', from === 'md' ? 'md:hidden' : 'lg:hidden', className)}>
      <div className="mx-auto flex max-w-2xl flex-col gap-2">{children}</div>
    </div>
  )
}
