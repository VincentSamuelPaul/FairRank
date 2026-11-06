import { ArrowLeft, LogOut, ShieldCheck } from 'lucide-react'
import { Link, NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useLogout, useMe, type Role } from '@/lib/auth'
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

export function AppShell({
  children,
  narrow = false,
  extra,
}: {
  children: React.ReactNode
  narrow?: boolean
  extra?: React.ReactNode
}) {
  const { data: user } = useMe()
  const logout = useLogout()
  return (
    <div className="min-h-screen bg-background">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-background focus:p-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-b bg-background/90 backdrop-blur">
        <div className={cn('mx-auto flex items-center justify-between gap-3 px-4 py-2.5', narrow ? 'max-w-2xl' : 'max-w-6xl')}>
          <div className="flex items-center gap-5">
            <Link to="/" className="flex items-center gap-1.5 font-semibold tracking-tight">
              <ShieldCheck className="size-4 text-primary" aria-hidden /> FairRank
            </Link>
            <nav aria-label="Main" className="flex gap-1">
              {user &&
                NAV[user.role].map((n) => (
                  <NavLink
                    key={n.to}
                    to={n.to}
                    className={({ isActive }) =>
                      cn('rounded-md px-2 py-1 text-sm', isActive ? 'bg-accent font-medium text-accent-foreground' : 'text-muted-foreground hover:text-foreground')
                    }
                  >
                    {n.label}
                  </NavLink>
                ))}
            </nav>
          </div>
          <div className="flex items-center gap-2 text-sm">
            {extra}
            <span className="hidden text-right leading-tight text-muted-foreground md:block">
              <span className="block text-foreground">{user?.full_name}</span>
              <span className="block text-xs">
                {user ? ROLE_LABEL[user.role] : ''}
                {user?.client_org ? ` · ${user.client_org.name}` : ''}
              </span>
            </span>
            <Button variant="outline" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending} aria-label="Sign out">
              <LogOut /> <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
      </header>
      <main id="main" className={cn('mx-auto px-4 pb-24 pt-6 sm:pt-8', narrow ? 'max-w-2xl' : 'max-w-6xl')}>
        {children}
      </main>
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
        <Link to={back.to} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-3.5" aria-hidden /> {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <div className="text-sm text-muted-foreground">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  )
}
