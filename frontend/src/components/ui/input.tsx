import * as React from 'react'
import { Input as InputPrimitive } from '@base-ui/react/input'
import { cn } from '@/lib/utils'

/**
 * Field surface: one step LIGHTER than the card it sits on (raised), a 1px border, a signal border and 3px signal glow on focus
 * (120ms), and a red border on error (the message beside it carries an icon, so colour is never the only signal).
 */
export const control =
  'w-full min-w-0 rounded-input border bg-surface-2 px-3.5 text-body text-text-1 outline-none transition-[border-color,box-shadow] duration-(--dur-instant) placeholder:text-text-3 hover:border-border-strong focus-visible:border-signal focus-visible:ring-3 focus-visible:ring-signal/25 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-bad aria-invalid:ring-bad/20'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return <InputPrimitive type={type} data-slot="input" className={cn(control, 'h-12', className)} {...props} />
}

export { Input }
