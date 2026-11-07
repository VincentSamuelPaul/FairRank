import { AlertCircle } from 'lucide-react'
import * as React from 'react'
import { control } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

/** Grows with its content; optional "n / max" counter. Works controlled (`value`) or with react-hook-form's register. */
export const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'> & { showCount?: boolean }>(({ className, showCount, onInput, value, maxLength, ...props }, ref) => {
  const inner = React.useRef<HTMLTextAreaElement | null>(null)
  const [len, setLen] = React.useState(typeof value === 'string' ? value.length : 0)
  const fit = React.useCallback(() => {
    const el = inner.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
    setLen(el.value.length)
  }, [])
  React.useLayoutEffect(fit, [fit, value])
  return (
    <div className="relative">
      <textarea
        ref={(el) => {
          inner.current = el
          if (typeof ref === 'function') ref(el)
          else if (ref) ref.current = el
        }}
        value={value}
        maxLength={maxLength}
        onInput={(e) => {
          fit()
          onInput?.(e)
        }}
        className={cn(control, 'min-h-28 resize-none overflow-hidden py-3', showCount && 'pb-8', className)}
        {...props}
      />
      {showCount && (
        <span aria-hidden className="tnum pointer-events-none absolute bottom-2.5 right-3.5 text-micro text-text-3">
          {len}{maxLength ? ` / ${maxLength}` : ''}
        </span>
      )}
    </div>
  )
})
Textarea.displayName = 'Textarea'

/** Native select, same surface as the other fields (use Listbox where a richer, keyboard-friendly picker is wanted). */
export const Select = React.forwardRef<HTMLSelectElement, React.ComponentProps<'select'>>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(control, 'h-12 pr-8', className)} {...props}>
    {children}
  </select>
))
Select.displayName = 'Select'

/** Inline message with an icon: an error is never conveyed by colour alone. */
export function FieldError({ message }: { message?: string }) {
  return message ? (
    <p role="alert" className="flex items-start gap-1.5 text-small text-bad">
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
      {message}
    </p>
  ) : null
}

export function Hint({ children }: { children: React.ReactNode }) {
  return <p className="text-small text-text-3">{children}</p>
}

/** Label above, control below, helper text underneath, error with icon. */
export function Field({ label, htmlFor, hint, error, children, className, aside }: { label: string; htmlFor: string; hint?: React.ReactNode; error?: string; children: React.ReactNode; className?: string; aside?: React.ReactNode }) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor={htmlFor}>{label}</Label>
        {aside}
      </div>
      {children}
      {hint && !error && <Hint>{hint}</Hint>}
      <FieldError message={error} />
    </div>
  )
}
