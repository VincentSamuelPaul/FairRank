import * as React from 'react'
import { cn } from '@/lib/utils'

/** Workspace card: solid surface, 1px border, no blur (blur is Showcase only). */
function Card({ className, size = 'default', ...props }: React.ComponentProps<'div'> & { size?: 'default' | 'sm' }) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        'flex flex-col gap-(--card-spacing) overflow-hidden rounded-card border bg-surface-1 py-(--card-spacing) text-small text-text-1 [--card-spacing:--spacing(5)] data-[size=sm]:[--card-spacing:--spacing(4)]',
        className,
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-header" className={cn('grid auto-rows-min items-start gap-1 px-(--card-spacing)', className)} {...props} />
}

function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-title" className={cn('text-h2', className)} {...props} />
}

function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-description" className={cn('text-small text-text-2', className)} {...props} />
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-content" className={cn('px-(--card-spacing)', className)} {...props} />
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-footer" className={cn('flex items-center border-t px-(--card-spacing) pt-(--card-spacing)', className)} {...props} />
}

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
