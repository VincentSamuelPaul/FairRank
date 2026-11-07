import { Check, TriangleAlert, X } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { cn } from '@/lib/utils'

type Tone = 'ok' | 'bad' | 'info'
interface ToastAction { label: string; onClick: () => void }
interface ToastItem { id: number; title: string; tone: Tone; action?: ToastAction }
interface Api { toast: (title: string, tone?: Tone, action?: ToastAction) => void }

const Ctx = createContext<Api>({ toast: () => {} }) // safe no-op outside a provider (tests, stories)
export const useToast = () => useContext(Ctx)

let next = 1

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const dismiss = useCallback((id: number) => setItems((l) => l.filter((t) => t.id !== id)), [])
  const toast = useCallback(
    (title: string, tone: Tone = 'info', action?: ToastAction) => {
      const id = next++
      setItems((l) => [...l.slice(-2), { id, title, tone, action }])
      setTimeout(() => dismiss(id), action ? 8000 : 5000)
    },
    [dismiss],
  )
  const api = useMemo(() => ({ toast }), [toast])
  return (
    <Ctx.Provider value={api}>
      {children}
      <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-(--gutter) bottom-4 z-50 flex flex-col items-stretch gap-2 sm:inset-x-auto sm:right-(--gutter) sm:w-96">
        {items.map((t) => (
          <div key={t.id} className="pointer-events-auto flex items-start gap-3 rounded-card border bg-surface-2 p-3.5 text-small text-text-1 shadow-float animate-in fade-in slide-in-from-bottom-2">
            {t.tone === 'bad' ? <TriangleAlert className="mt-0.5 size-4 shrink-0 text-bad" aria-hidden /> : <Check className={cn('mt-0.5 size-4 shrink-0', t.tone === 'ok' ? 'text-ok' : 'text-info')} aria-hidden />}
            <p className="flex-1">{t.title}</p>
            {t.action && (
              <button type="button" onClick={() => { t.action!.onClick(); dismiss(t.id) }} className="-my-1 rounded-pill px-3 py-1 text-small font-medium text-signal hover:bg-surface-1">
                {t.action.label}
              </button>
            )}
            <button type="button" aria-label="Dismiss" onClick={() => dismiss(t.id)} className="rounded-pill p-0.5 text-text-2 hover:text-text-1">
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
