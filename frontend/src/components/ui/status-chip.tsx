import { cva, type VariantProps } from 'class-variance-authority'
import type { Stage } from '@/lib/types'
import { stageLabel } from '@/lib/format'
import { cn } from '@/lib/utils'

const chip = cva('inline-flex h-6 shrink-0 items-center gap-1.5 rounded-pill border px-2.5 text-micro uppercase', {
  variants: { tone: { neutral: 'border-border text-text-2', ok: 'border-border text-text-1', warn: 'border-border text-text-1', bad: 'border-border text-text-1', info: 'border-border text-text-1' } },
  defaultVariants: { tone: 'neutral' },
})
const dot = { neutral: 'bg-text-3', ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad', info: 'bg-info' }

export type ChipTone = NonNullable<VariantProps<typeof chip>['tone']>

/** Pipeline stage or flag. Micro type, 1px border, small dot. The dot carries the status colour; the word carries the meaning. */
export function StatusChip({ children, tone = 'neutral', muted = false, className }: { children: React.ReactNode; tone?: ChipTone; muted?: boolean; className?: string }) {
  return (
    <span className={cn(chip({ tone }), muted && 'text-text-3 line-through decoration-1', className)}>
      <span aria-hidden className={cn('size-1.5 rounded-pill', dot[tone])} />
      {children}
    </span>
  )
}

/** Every pipeline stage has its own hue (dot + 12% tint). The label still names the stage, so colour is never the only signal. */
export function StageChip({ stage, className }: { stage: Stage; className?: string }) {
  return (
    <span
      style={{ '--h': `var(--stage-${stage})` } as React.CSSProperties}
      className={cn(
        'inline-flex h-6 shrink-0 items-center gap-1.5 rounded-pill border border-[color-mix(in_srgb,var(--h)_30%,transparent)] bg-[color-mix(in_srgb,var(--h)_12%,transparent)] px-2.5 text-micro uppercase text-text-1',
        stage === 'rejected' && 'text-text-2 line-through decoration-1',
        className,
      )}
    >
      <span aria-hidden className="size-1.5 rounded-pill bg-(--h)" />
      {stageLabel(stage)}
    </span>
  )
}
