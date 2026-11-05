import { Button } from '@/components/ui/button'
import { useLogout, useMe } from '@/lib/auth'

const ROLE_LABEL = { recruiter: 'Recruiter', client: 'Hiring manager', delivery_head: 'Delivery head' } as const

export function AppShell({ title, children }: { title: string; children: React.ReactNode }) {
  const { data: user } = useMe()
  const logout = useLogout()
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <span className="font-semibold tracking-tight">FairRank</span>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-muted-foreground sm:inline">
              {user?.full_name} · {user ? ROLE_LABEL[user.role] : ''}
              {user?.client_org ? ` · ${user.client_org.name}` : ''}
            </span>
            <Button variant="outline" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {children}
      </main>
    </div>
  )
}
