import * as React from 'react'
import { control } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'>>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(control, 'min-h-24 py-2.5', className)} {...props} />
))
Textarea.displayName = 'Textarea'

export const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<'select'>>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(control, 'h-11 pr-8', className)} {...props}>
    {children}
  </select>
))
Select.displayName = 'Select'

export function FieldError({ message }: { message?: string }) {
  return message ? (
    <p role="alert" className="text-small text-bad">
      {message}
    </p>
  ) : null
}

export function Hint({ children }: { children: React.ReactNode }) {
  return <p className="text-small text-text-2">{children}</p>
}

/** Label above, control below, optional hint and error. */
export function Field({ label, htmlFor, hint, error, children, className }: { label: string; htmlFor: string; hint?: React.ReactNode; error?: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && !error && <Hint>{hint}</Hint>}
      <FieldError message={error} />
    </div>
  )
}
