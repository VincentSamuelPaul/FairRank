import { cn } from '@/lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('animate-pulse rounded-input bg-surface-2', className)} />
}

export function ListSkeleton({ rows = 4, className }: { rows?: number; className?: string }) {
  return (
    <div role="status" aria-label="Loading" className={cn('space-y-3', className)}>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-28 w-full rounded-card" />
      ))}
    </div>
  )
}

/** Same grid as CandidateRow, so the page does not jump when data arrives. */
export function RowSkeleton() {
  return (
    <li aria-hidden className="surface-card grid grid-cols-1 gap-y-3 rounded-card border p-4 pl-5 md:grid-cols-[7rem_1fr_11rem] md:gap-x-6 md:p-5 md:pl-6">
      <div className="flex items-center gap-3 md:flex-col md:gap-2 md:row-span-2"><Skeleton className="h-6 w-5" /><Skeleton className="size-14 rounded-pill" /><Skeleton className="h-3 w-12" /></div>
      <div className="space-y-2 md:col-start-2"><Skeleton className="h-6 w-1/2" /><Skeleton className="h-3.5 w-3/4" /></div>
      <div className="flex gap-2 md:col-start-2"><Skeleton className="h-8 w-1/2 rounded-pill" /><Skeleton className="h-8 w-2/5 rounded-pill" /></div>
      <div className="flex flex-col gap-2 md:col-start-3 md:row-span-2 md:row-start-1 md:items-end"><Skeleton className="h-11 w-full rounded-pill md:w-32" /><Skeleton className="h-9 w-full rounded-pill md:w-32" /></div>
    </li>
  )
}

export function RowListSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <ul role="status" aria-label="Loading" className="space-y-3">
      {Array.from({ length: rows }, (_, i) => <RowSkeleton key={i} />)}
    </ul>
  )
}
