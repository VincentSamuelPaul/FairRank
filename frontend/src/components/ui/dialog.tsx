import { X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  /** Wider dialog for forms with a long text field. */
  wide?: boolean
}

/** A native <dialog>: focus trap, Esc to close and a backdrop for free. A bottom sheet on phones. */
export function Dialog({ open, onClose, title, description, children, wide = false }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      className={`modal surface-card w-full ${wide ? 'max-w-xl' : 'max-w-md'} rounded-card border p-0 text-text-1 shadow-float`}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
    >
      {open && (
        <div className="max-h-[85dvh] space-y-4 overflow-y-auto p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 id={titleId}>{title}</h2>
              {description && <p className="text-small text-text-2">{description}</p>}
            </div>
            <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close">
              <X />
            </Button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  )
}
