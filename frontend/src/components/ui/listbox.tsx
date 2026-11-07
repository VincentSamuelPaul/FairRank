import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { control } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface ListboxOption {
  value: string
  label: string
  /** Optional leading element, e.g. a client Monogram. */
  icon?: React.ReactNode
}

/**
 * A custom select. Keyboard: Arrow keys move, Home/End jump, Enter or Space picks, Esc closes, typing jumps to a match.
 * Focus stays on the button; the highlighted option is announced through aria-activedescendant.
 */
export function Listbox({ id, value, onChange, options, placeholder = 'Select…', invalid, disabled, className, ...aria }: {
  id?: string
  value: string
  onChange: (v: string) => void
  options: ListboxOption[]
  placeholder?: string
  invalid?: boolean
  disabled?: boolean
  className?: string
  'aria-label'?: string
}) {
  const uid = useId()
  const box = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const selected = options.findIndex((o) => o.value === value)
  const [active, setActive] = useState(Math.max(selected, 0))
  const typed = useRef({ text: '', at: 0 })

  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [open])
  useEffect(() => {
    if (open) document.getElementById(`${uid}-${active}`)?.scrollIntoView({ block: 'nearest' })
  }, [open, active, uid])

  const pick = (i: number) => {
    const o = options[i]
    if (!o) return
    onChange(o.value)
    setOpen(false)
  }
  const onKey = (e: React.KeyboardEvent) => {
    if (disabled) return
    if (e.key === 'Escape' && open) { e.stopPropagation(); e.preventDefault(); setOpen(false); return }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
      e.preventDefault()
      if (!open) { setOpen(true); setActive(Math.max(selected, 0)); return }
      setActive((a) => (e.key === 'ArrowDown' ? Math.min(a + 1, options.length - 1) : e.key === 'ArrowUp' ? Math.max(a - 1, 0) : e.key === 'Home' ? 0 : options.length - 1))
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      open ? pick(active) : (setOpen(true), setActive(Math.max(selected, 0)))
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      const t = typed.current
      t.text = Date.now() - t.at > 600 ? e.key.toLowerCase() : t.text + e.key.toLowerCase()
      t.at = Date.now()
      const i = options.findIndex((o) => o.label.toLowerCase().startsWith(t.text))
      if (i >= 0) { setActive(i); if (!open) onChange(options[i].value) }
    }
  }

  const cur = options[selected]
  return (
    <div ref={box} className="relative">
      <button
        id={id}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${uid}-list`}
        aria-activedescendant={open ? `${uid}-${active}` : undefined}
        aria-invalid={invalid || undefined}
        disabled={disabled}
        onClick={() => { setOpen((o) => !o); setActive(Math.max(selected, 0)) }}
        onKeyDown={onKey}
        className={cn(control, 'flex h-12 items-center gap-3 text-left', className)}
        {...aria}
      >
        {cur?.icon}
        <span className={cn('min-w-0 flex-1 truncate', !cur && 'text-text-3')}>{cur?.label ?? placeholder}</span>
        <ChevronDown className={cn('size-4 shrink-0 text-text-2 transition-transform duration-(--dur-fast)', open && 'rotate-180')} aria-hidden />
      </button>
      {open && (
        <ul id={`${uid}-list`} role="listbox" className="absolute inset-x-0 top-full z-30 mt-1.5 max-h-64 overflow-y-auto rounded-card border bg-surface-2 p-1.5 shadow-float">
          {options.map((o, i) => (
            <li
              key={o.value}
              id={`${uid}-${i}`}
              role="option"
              aria-selected={o.value === value}
              onMouseMove={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(i)}
              className={cn('flex min-h-11 cursor-pointer items-center gap-3 rounded-input px-3 text-body', i === active && 'bg-surface-1 shadow-[inset_2px_0_0_var(--signal)]')}
            >
              {o.icon}
              <span className="min-w-0 flex-1 truncate">{o.label}</span>
              {o.value === value && <Check className="size-4 text-text-1" aria-hidden />}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
