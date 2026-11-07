import { Briefcase, CornerDownLeft, Plus, Search, User } from 'lucide-react'
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMe } from '@/lib/auth'
import { useAllRanked, useRequisitions } from '@/lib/queries'
import { cn } from '@/lib/utils'

interface Item {
  id: string
  group: 'Actions' | 'Requisitions' | 'Candidates'
  label: string
  hint?: string
  icon: React.ReactNode
  run: () => void
}

/** Cmd/Ctrl+K: jump to a requisition or candidate, or start a new requisition. Staff only. */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const role = useMe().data?.role
  const listId = useId()
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const reqs = useRequisitions()
  const ranked = useAllRanked(reqs.data?.map((r) => r.id) ?? [], open)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) {
      d.showModal()
      setQ('')
      setActive(0)
      requestAnimationFrame(() => input.current?.focus())
    }
    if (!open && d.open) d.close()
  }, [open])

  const items = useMemo<Item[]>(() => {
    const go = (to: string) => () => { onClose(); navigate(to) }
    const out: Item[] = []
    if (role === 'recruiter') out.push({ id: 'new', group: 'Actions', label: 'New requisition', hint: 'Paste a JD', icon: <Plus className="size-4" />, run: go('/requisitions?new=1') })
    out.push({ id: 'reqs', group: 'Actions', label: 'All requisitions', icon: <Briefcase className="size-4" />, run: go('/requisitions') })
    for (const r of reqs.data ?? []) out.push({ id: `r-${r.id}`, group: 'Requisitions', label: r.title, hint: r.client.name, icon: <Briefcase className="size-4" />, run: go(`/requisitions/${r.id}`) })
    ranked.forEach((qr, i) => {
      const req = reqs.data?.[i]
      for (const c of qr.data?.candidates ?? [])
        out.push({ id: `c-${c.id}`, group: 'Candidates', label: c.full_name || c.original_name || 'Unnamed CV', hint: `${req?.title ?? ''}${c.current_role ? ` · ${c.current_role}` : ''}`, icon: <User className="size-4" />, run: go(`/candidates/${c.id}`) })
    })
    return out
  }, [reqs.data, ranked, role, navigate, onClose])

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const hit = (i: Item) => !needle || `${i.label} ${i.hint ?? ''}`.toLowerCase().includes(needle)
    const g = (name: Item['group'], max: number) => items.filter((i) => i.group === name && hit(i)).slice(0, max)
    return [...g('Actions', 4), ...g('Requisitions', 6), ...g('Candidates', 8)]
  }, [items, q])

  useEffect(() => setActive(0), [q])

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, shown.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); shown[active]?.run() }
  }
  useEffect(() => document.getElementById(`${listId}-${active}`)?.scrollIntoView({ block: 'nearest' }), [active, listId])

  let lastGroup = ''
  return (
    <dialog
      ref={ref}
      aria-label="Command palette"
      className="modal palette w-[calc(100%-2*var(--gutter))] max-w-xl rounded-card border bg-surface-2 p-0 text-text-1 shadow-float"
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
    >
      {open && (
        <div onKeyDown={onKey}>
          <div className="flex items-center gap-3 border-b px-4">
            <Search className="size-4 text-text-2" aria-hidden />
            <input
              ref={input}
              role="combobox"
              aria-expanded
              aria-controls={listId}
              aria-activedescendant={shown[active] ? `${listId}-${active}` : undefined}
              aria-label="Search requisitions and candidates"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Jump to a requisition or candidate…"
              className="h-14 w-full bg-transparent text-body outline-none placeholder:text-text-3"
            />
            <kbd className="rounded-xs border px-1.5 py-0.5 text-micro text-text-2">Esc</kbd>
          </div>
          <ul id={listId} role="listbox" className="max-h-[50vh] overflow-y-auto p-2">
            {shown.length === 0 && <li className="px-3 py-8 text-center text-small text-text-2">{reqs.isPending || ranked.some((r) => r.isPending) ? 'Loading…' : 'Nothing matches.'}</li>}
            {shown.map((it, i) => {
              const head = it.group !== lastGroup
              lastGroup = it.group
              return (
                <li key={it.id} role="presentation">
                  {head && <p className="px-3 pb-1 pt-3 text-micro uppercase text-text-2">{it.group}</p>}
                  <div
                    id={`${listId}-${i}`}
                    role="option"
                    aria-selected={i === active}
                    onMouseMove={() => setActive(i)}
                    onClick={it.run}
                    className={cn('flex min-h-11 cursor-pointer items-center gap-3 rounded-input px-3 text-small', i === active && 'bg-surface-1 shadow-[inset_2px_0_0_var(--signal)]')}
                  >
                    <span className="text-text-2" aria-hidden>{it.icon}</span>
                    <span className="min-w-0 flex-1 truncate">{it.label}</span>
                    {it.hint && <span className="hidden max-w-[45%] truncate text-text-2 sm:block">{it.hint}</span>}
                    {i === active && <CornerDownLeft className="size-3.5 text-text-2" aria-hidden />}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </dialog>
  )
}
