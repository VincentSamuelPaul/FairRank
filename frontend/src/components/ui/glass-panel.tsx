import { cn } from '@/lib/utils'

/** SHOWCASE ONLY (login, landing). Frosted: translucent fill, 1px border, blur. Workspace and Portal never use it. */
export function GlassPanel({ children, strong = false, rule = false, className }: { children: React.ReactNode; strong?: boolean; rule?: boolean; className?: string }) {
  return (
    <div className={cn('relative rounded-card border backdrop-blur-(--blur-glass)', strong ? 'bg-glass-strong' : 'bg-glass', className)}>
      {rule && <HairlineRule className="absolute inset-x-4 top-0" />}
      {children}
    </div>
  )
}

/** 1px rule; the first 15% is brighter, like the reference's progress mark. */
export function HairlineRule({ className }: { className?: string }) {
  return <div aria-hidden className={cn('h-px w-full bg-[linear-gradient(90deg,var(--text-1)_0_15%,var(--border)_15%_100%)]', className)} />
}
