import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Icon, one sentence, one action. */
export function EmptyState({
  title,
  children,
  action,
  icon,
  className,
}: {
  title: string
  children?: React.ReactNode
  action?: React.ReactNode
  icon?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex flex-col items-center gap-2 rounded-card border border-dashed border-border-strong px-6 py-12 text-center', className)}>
      <span className="text-text-2" aria-hidden>{icon ?? <Inbox className="size-6" />}</span>
      <p className="text-body font-medium">{title}</p>
      {children && <p className="max-w-md text-small text-text-2">{children}</p>}
      {action && <div className="pt-2">{action}</div>}
    </div>
  )
}
