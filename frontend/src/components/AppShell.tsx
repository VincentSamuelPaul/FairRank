import { ArrowLeft, Search } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { CommandPalette } from '@/components/CommandPalette'
import { useLogout, useMe, type Role, type User } from '@/lib/auth'
import { cn } from '@/lib/utils'

const ROLE_LABEL: Record<Role, string> = { recruiter: 'Recruiter', client: 'Hiring manager', delivery_head: 'Delivery head' }
const NAV: Record<Role, { to: string; label: string }[]> = {
  recruiter: [{ to: '/requisitions', label: 'Requisitions' }],
  delivery_head: [
    { to: '/pipeline', label: 'Pipeline' },
    { to: '/requisitions', label: 'Requisitions' },
  ],
  client: [],
}

const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?'

/** Initials avatar that opens a small account menu. Esc and outside click close it. */
function UserMenu({ user }: { user: User }) {
  const logout = useLogout()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', esc)
    }
  }, [open])
  return (
    <div ref={box} className="relative">
      <button
        type="button"
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="grid size-11 place-items-center rounded-pill border border-border-strong bg-surface-2 text-small font-medium transition-colors duration-(--dur-fast) hover:bg-surface-1"
      >
        {initials(user.full_name)}
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-30 mt-2 w-64 rounded-card border bg-surface-2 p-2 shadow-float">
          <div className="px-3 py-2">
            <p className="text-body font-medium">{user.full_name}</p>
            <p className="text-small text-text-2">
              {ROLE_LABEL[user.role]}
              {user.client_org ? ` · ${user.client_org.name}` : ''}
            </p>
          </div>
          <button role="menuitem" type="button" disabled={logout.isPending} onClick={() => logout.mutate()} className="flex min-h-11 w-full items-center rounded-input px-3 text-small hover:bg-surface-1">
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

/** `fill`: the page does not scroll; the workspace fills the viewport under the top bar and its panes scroll on their own. */
export function AppShell({ children, narrow = false, extra, fill = false }: { children: React.ReactNode; narrow?: boolean; extra?: React.ReactNode; fill?: boolean }) {
  const { data: user } = useMe()
  const staff = !!user && user.role !== 'client'
  const [palette, setPalette] = useState(false)
  useEffect(() => {
    if (!staff) return
    const on = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPalette((o) => !o)
      }
    }
    window.addEventListener('keydown', on)
    return () => window.removeEventListener('keydown', on)
  }, [staff])
  const wrap = narrow ? 'max-w-2xl' : fill ? 'max-w-[1500px]' : 'max-w-6xl'
  return (
    <div className={cn('relative bg-ws', fill ? 'flex h-dvh flex-col overflow-hidden' : 'min-h-screen')}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface-2 focus:p-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-20 h-(--header-h) bg-ws">
        <div className={cn('mx-auto flex h-full items-center justify-between gap-3 px-(--gutter)', wrap)}>
          <div className="flex h-full min-w-0 items-center gap-3 sm:gap-6">
            <Link to="/" className="flex min-h-11 items-center gap-2 text-body font-medium tracking-tight">
              <svg aria-hidden viewBox="0 0 24 24" className="size-5 text-text-1" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3 4 6v6c0 4.5 3.2 7.8 8 9 4.8-1.2 8-4.5 8-9V6l-8-3Z" />
                <path d="m8.5 12 2.5 2.5 4.5-5" />
              </svg>
              FairRank
            </Link>
            <nav aria-label="Main" className="flex h-full">
              {user &&
                NAV[user.role].map((n) => (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    className={({ isActive }) =>
                      cn('flex h-full items-center px-2 text-small transition-colors sm:px-3 duration-(--dur-fast)', isActive ? 'font-medium text-text-1 shadow-[inset_0_-2px_0_var(--accent),0_8px_16px_-6px_color-mix(in_srgb,var(--accent)_45%,transparent)]' : 'text-text-2 hover:text-text-1')
                    }
                  >
                    {n.label}
                  </NavLink>
                ))}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            {extra}
            {staff && (
              <button
                type="button"
                onClick={() => setPalette(true)}
                aria-label="Search (Ctrl K)"
                className="flex h-11 items-center gap-2 rounded-pill border border-border-strong px-3.5 text-small text-text-2 transition-colors duration-(--dur-fast) hover:bg-surface-2 hover:text-text-1"
              >
                <Search className="size-4" aria-hidden />
                <span className="max-md:hidden">Search</span>
                <kbd className="rounded-xs border px-1.5 text-micro max-md:hidden">⌘K</kbd>
              </button>
            )}
            {user && <UserMenu user={user} />}
          </div>
        </div>
        {/* hairline that fades out at both ends */}
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-px bg-[linear-gradient(90deg,transparent,var(--border-strong)_22%,var(--border-strong)_78%,transparent)]" />
      </header>
      <div aria-hidden className="page-wash pointer-events-none fixed inset-x-0 top-0 z-0 h-[360px]" />
      <main id="main" className={cn('page-enter relative mx-auto w-full px-(--gutter)', fill ? 'flex min-h-0 flex-1 flex-col pt-2' : 'pb-24 pt-6 sm:pt-8', wrap)}>
        {children}
      </main>
      {staff && <CommandPalette open={palette} onClose={() => setPalette(false)} />}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  back,
  actions,
}: {
  title: string
  subtitle?: React.ReactNode
  back?: { to: string; label: string }
  actions?: React.ReactNode
}) {
  return (
    <div className="mb-6 space-y-2">
      {back && (
        <Link to={back.to} className="inline-flex min-h-11 items-center gap-1 text-small text-text-2 hover:text-text-1">
          <ArrowLeft className="size-3.5" aria-hidden /> {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1>{title}</h1>
          {subtitle && <div className="text-small text-text-2">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
