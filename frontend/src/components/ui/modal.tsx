import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
}

/** A native <dialog>: focus trap, Esc to close and a backdrop for free. A bottom sheet on phones. */
export function Modal({ open, onClose, title, description, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      className="modal w-full max-w-md rounded-card border bg-surface-2 p-0 text-text-1 shadow-float"
      aria-labelledby="modal-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
    >
      {open && (
        <div className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1">
              <h2 id="modal-title" className="text-base font-semibold">
                {title}
              </h2>
              {description && <p className="text-sm text-muted-foreground">{description}</p>}
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
