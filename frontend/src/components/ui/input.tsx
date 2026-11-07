import * as React from 'react'
import { Input as InputPrimitive } from '@base-ui/react/input'
import { cn } from '@/lib/utils'

export const control =
  'w-full min-w-0 rounded-input border border-border-strong bg-surface-1 px-3.5 text-body text-text-1 outline-none transition-colors duration-(--dur-fast) placeholder:text-text-3 focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-bad'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return <InputPrimitive type={type} data-slot="input" className={cn(control, 'h-11', className)} {...props} />
}

export { Input }
