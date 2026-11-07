import { Loader2 } from 'lucide-react'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { ListSkeleton, Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('size-4 animate-spin', className)} aria-hidden />
}

export { EmptyState, ErrorState, ListSkeleton, Skeleton }

interface Q<T> {
  data: T | undefined
  isPending: boolean
  isError: boolean
  error: unknown
  refetch: () => unknown
}

/** One place for loading / error / empty handling so every list and page gets all three. */
export function Async<T>({
  query,
  skeleton,
  isEmpty,
  empty,
  children,
}: {
  query: Q<T>
  skeleton?: React.ReactNode
  isEmpty?: (data: T) => boolean
  empty?: React.ReactNode
  children: (data: T) => React.ReactNode
}) {
  if (query.isPending) return <>{skeleton ?? <ListSkeleton />}</>
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  if (query.data === undefined) return null
  if (isEmpty?.(query.data)) return <>{empty}</>
  return <>{children(query.data)}</>
}
