import { NavLink, Outlet, useParams } from 'react-router-dom'
import { AppShell, PageHeader } from '@/components/AppShell'
import { Async, Skeleton } from '@/components/states'
import { notice, years } from '@/lib/format'
import { useRequisition } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { useMe } from '@/lib/auth'

const TABS = [
  { to: '', label: 'Ranked list', end: true, staff: true },
  { to: 'upload', label: 'Upload CVs', staff: false },
  { to: 'scorecard', label: 'Scorecard', staff: true },
  { to: 'pipeline', label: 'Pipeline', staff: true },
]

export function RequisitionLayout() {
  const { id = '' } = useParams()
  const { data: user } = useMe()
  const query = useRequisition(id)
  return (
    <AppShell>
      <Async query={query} skeleton={<Skeleton className="h-16 w-full" />}>
        {(req) => (
          <PageHeader
            back={{ to: '/requisitions', label: 'All requisitions' }}
            title={req.title}
            subtitle={
              <>
                {req.client.name}
                {req.location && ` · ${req.location}`}
                {req.exp_min_years !== null && ` · ${years(req.exp_min_years)}–${years(req.exp_max_years)}`}
                {req.notice_max_days !== null && ` · notice ≤ ${notice(req.notice_max_days)}`}
                {req.scorecard_version && ` · scorecard v${req.scorecard_version}`}
              </>
            }
          />
        )}
      </Async>
      <nav aria-label="Requisition sections" className="-mt-2 mb-6 flex gap-1 overflow-x-auto border-b">
        {TABS.filter((t) => t.staff || user?.role === 'recruiter').map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              cn(
                '-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm',
                isActive ? 'border-primary font-medium text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
              )
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </AppShell>
  )
}
