import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { homeFor, useMe, type Role } from '@/lib/auth'

export function FullPageMessage({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center p-6 text-sm text-muted-foreground">{children}</div>
}

/** Route guard: signed out -> /login; wrong role -> that user's own home. */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { data: user, isPending, isError, refetch } = useMe()
  const location = useLocation()

  if (isPending) return <FullPageMessage>Loading…</FullPageMessage>
  if (isError)
    return (
      <FullPageMessage>
        <div className="space-y-3 text-center">
          <p>We couldn’t reach the server.</p>
          <button className="underline" onClick={() => refetch()}>
            Try again
          </button>
        </div>
      </FullPageMessage>
    )
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />
  return <Outlet />
}
