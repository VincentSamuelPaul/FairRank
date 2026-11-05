import { Navigate, Route, Routes } from 'react-router-dom'
import { FullPageMessage, RequireRole } from '@/components/RequireRole'
import { homeFor, useMe } from '@/lib/auth'
import { LoginPage } from '@/pages/LoginPage'
import { Placeholder } from '@/pages/Placeholder'

function RoleRedirect() {
  const { data: user, isPending } = useMe()
  if (isPending) return <FullPageMessage>Loading…</FullPageMessage>
  return <Navigate to={user ? homeFor(user.role) : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireRole roles={['recruiter']} />}>
        <Route path="/requisitions" element={<Placeholder title="Requisitions" note="JD intake and scorecards arrive on Friday." />} />
      </Route>
      <Route element={<RequireRole roles={['delivery_head']} />}>
        <Route path="/pipeline" element={<Placeholder title="Pipeline and agreement report" note="Pipeline board and the AI-vs-recruiter report arrive on Sunday." />} />
      </Route>
      <Route element={<RequireRole roles={['client']} />}>
        <Route path="/portal" element={<Placeholder title="Your shortlist" note="The client portal arrives on Sunday." />} />
      </Route>
      <Route path="*" element={<RoleRedirect />} />
    </Routes>
  )
}
