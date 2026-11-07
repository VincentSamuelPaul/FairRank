import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

/** What happened, and a retry. */
export function ErrorState({ error, onRetry, title = 'We couldn’t load this', className }: { error?: unknown; onRetry?: () => void; title?: string; className?: string }) {
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div role="alert" className={cn('flex flex-col items-center gap-2 rounded-card border border-bad/40 bg-surface-1 px-6 py-10 text-center', className)}>
      <AlertCircle className="size-6 text-bad" aria-hidden />
      <p className="text-body font-medium">{title}</p>
      <p className="text-small text-text-2">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-2">
          Try again
        </Button>
      )}
    </div>
  )
}
