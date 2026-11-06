import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import { FullPageMessage, RequireRole } from '@/components/RequireRole'
import { homeFor, useMe } from '@/lib/auth'
import { LoginPage } from '@/pages/LoginPage'
import { AgreementReportPage, PipelineOverviewPage } from '@/pages/head/DeliveryHeadPage'
import { PortalCandidatePage } from '@/pages/portal/PortalCandidatePage'
import { PortalPage } from '@/pages/portal/PortalPage'
import { CandidatePage } from '@/pages/recruiter/CandidatePage'
import { PipelinePage } from '@/pages/recruiter/PipelinePage'
import { RankedPage } from '@/pages/recruiter/RankedPage'
import { RequisitionLayout } from '@/pages/recruiter/RequisitionLayout'
import { RequisitionsPage } from '@/pages/recruiter/RequisitionsPage'
import { ScorecardPage } from '@/pages/recruiter/ScorecardPage'
import { UploadPage } from '@/pages/recruiter/UploadPage'

function RoleRedirect() {
  const { data: user, isPending } = useMe()
  if (isPending) return <FullPageMessage>Loading…</FullPageMessage>
  return <Navigate to={user ? homeFor(user.role) : '/login'} replace />
}

/** Only recruiters upload; the delivery head has read access to the rest. */
function RecruiterOnlyUpload() {
  const { data: user } = useMe()
  const { id } = useParams()
  return user?.role === 'recruiter' ? <UploadPage /> : <Navigate to={`/requisitions/${id}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireRole roles={['recruiter', 'delivery_head']} />}>
        <Route path="/requisitions" element={<RequisitionsPage />} />
        <Route path="/requisitions/:id" element={<RequisitionLayout />}>
          <Route index element={<RankedPage />} />
          <Route path="upload" element={<RecruiterOnlyUpload />} />
          <Route path="scorecard" element={<ScorecardPage />} />
          <Route path="pipeline" element={<PipelinePage />} />
        </Route>
        <Route path="/candidates/:id" element={<CandidatePage />} />
      </Route>
      <Route element={<RequireRole roles={['delivery_head']} />}>
        <Route path="/pipeline" element={<PipelineOverviewPage />} />
        <Route path="/pipeline/report" element={<AgreementReportPage />} />
      </Route>
      <Route element={<RequireRole roles={['client']} />}>
        <Route path="/portal" element={<PortalPage />} />
        <Route path="/portal/candidates/:id" element={<PortalCandidatePage />} />
      </Route>
      <Route path="*" element={<RoleRedirect />} />
    </Routes>
  )
}
