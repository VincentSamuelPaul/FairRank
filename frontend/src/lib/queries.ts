import { keepPreviousData, useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, post } from '@/lib/api'
import type {
  AgreementReport,
  CandidateDetail,
  ClientCard,
  PipelineColumn,
  PipelineSummary,
  PortalRequisition,
  RankedList,
  Requisition,
  Scorecard,
  Stage,
  UploadItem,
  Criterion,
} from '@/lib/types'

const qs = (params: Record<string, string | undefined>) => {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v)
  const s = q.toString()
  return s ? `?${s}` : ''
}

// --- requisitions
export const useClientOrgs = () =>
  useQuery({ queryKey: ['client-orgs'], queryFn: () => api<{ id: number; name: string }[]>('/api/client-orgs/') })

export const useRequisitions = () =>
  useQuery({ queryKey: ['requisitions'], queryFn: () => api<Requisition[]>('/api/requisitions/') })

export const useRequisition = (id: string) =>
  useQuery({ queryKey: ['requisition', id], queryFn: () => api<Requisition>(`/api/requisitions/${id}/`) })

export function useCreateRequisition() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: { client_org: number; title: string; jd_text: string }) =>
      post<{ requisition: Requisition; warning: string }>('/api/requisitions/', b),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['requisitions'] }),
  })
}

export function useUpdateRequisition(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (b: Partial<Requisition>) => api<Requisition>(`/api/requisitions/${id}/`, { method: 'PATCH', body: b }),
    onSuccess: (data) => {
      qc.setQueryData(['requisition', id], data)
      qc.invalidateQueries({ queryKey: ['requisitions'] })
    },
  })
}

/** `onSaved` runs even though the editor remounts on the new version (so the confirmation is never lost). */
export function useSaveScorecard(id: string, onSaved?: (card: Scorecard & { rescoring: number }) => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (criteria: Criterion[]) =>
      api<Scorecard & { rescoring: number }>(`/api/requisitions/${id}/scorecard/`, { method: 'PUT', body: { criteria } }),
    onSuccess: (card) => {
      qc.invalidateQueries({ queryKey: ['requisition', id] })
      qc.invalidateQueries({ queryKey: ['ranked', id] })
      onSaved?.(card)
    },
  })
}

// --- ranked list
export const useRanked = (id: string, params: { q?: string; band?: string; flag?: string; stage?: string }) =>
  useQuery({
    queryKey: ['ranked', id, params],
    queryFn: () => api<RankedList>(`/api/requisitions/${id}/candidates/${qs(params)}`),
    placeholderData: keepPreviousData,
    // keep polling while the worker is still parsing or scoring
    refetchInterval: (q) => (q.state.data && q.state.data.counts.processing > 0 ? 2000 : false),
  })

/** Ranked lists for many requisitions at once. Same cache key as an unfiltered `useRanked`, so opening a requisition is instant. */
export const useAllRanked = (ids: string[], enabled = true) =>
  useQueries({
    queries: ids.map((id) => ({
      queryKey: ['ranked', id, {}],
      queryFn: () => api<RankedList>(`/api/requisitions/${id}/candidates/`),
      enabled,
      staleTime: 15_000,
    })),
  })

// --- upload
export function useUploadStatus(reqId: string, ids: string[]) {
  return useQuery({
    queryKey: ['upload-status', reqId, ids.length],
    enabled: ids.length > 0,
    queryFn: () => api<{ items: UploadItem[]; in_progress: boolean }>(`/api/requisitions/${reqId}/uploads/?ids=${ids.join(',')}`),
    refetchInterval: (q) => (q.state.data?.in_progress === false ? false : 1500),
  })
}

export async function uploadBatch(reqId: string, files: File[]) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('consent_confirmed', 'true')
  return api<{ accepted: { candidate_id: string; name: string }[]; rejected: { name: string; reason: string }[] }>(
    `/api/requisitions/${reqId}/uploads/`,
    { method: 'POST', form },
  )
}

// --- candidate
export const useCandidate = (id: string) =>
  useQuery({
    queryKey: ['candidate', id],
    queryFn: () => api<CandidateDetail>(`/api/candidates/${id}/`),
    staleTime: Infinity, // every fetch writes a view-log row; do not refetch on focus or remount
    gcTime: 0,
  })

export function useCandidateActions(id: string, reqId?: string) {
  const qc = useQueryClient()
  const done = (data?: CandidateDetail) => {
    if (data) qc.setQueryData(['candidate', id], data)
    qc.invalidateQueries({ queryKey: ['ranked'] })
    qc.invalidateQueries({ queryKey: ['pipeline', reqId] })
  }
  return {
    submit: useMutation({
      mutationFn: (note: string) => post<CandidateDetail>(`/api/candidates/${id}/submit/`, { note }),
      onSuccess: done,
    }),
    move: useMutation({
      mutationFn: (stage: Stage) => post<CandidateDetail>(`/api/candidates/${id}/stage/`, { stage }),
      onSuccess: done,
    }),
    retry: useMutation({
      mutationFn: () => post(`/api/candidates/${id}/rescore/`),
      onSuccess: () => qc.invalidateQueries({ queryKey: ['ranked'] }),
    }),
    remove: useMutation({
      mutationFn: (requester: string) => post(`/api/candidates/${id}/delete/`, { requester, confirm: true }),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['ranked'] })
        qc.invalidateQueries({ queryKey: ['pipeline'] })
        qc.invalidateQueries({ queryKey: ['requisitions'] })
      },
    }),
  }
}

export function useRetryScoring() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => post(`/api/candidates/${id}/rescore/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ranked'] }),
  })
}

export function useMoveStage(reqId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (v: { id: string; stage: Stage }) => post(`/api/candidates/${v.id}/stage/`, { stage: v.stage }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline', reqId] })
      qc.invalidateQueries({ queryKey: ['ranked', reqId] })
    },
  })
}

// --- pipeline & reports
export const usePipeline = (reqId: string) =>
  useQuery({
    queryKey: ['pipeline', reqId],
    queryFn: () => api<{ requisition: Requisition; columns: PipelineColumn[] }>(`/api/requisitions/${reqId}/pipeline/`),
  })

export const usePipelineSummary = () =>
  useQuery({ queryKey: ['pipeline-summary'], queryFn: () => api<PipelineSummary[]>('/api/pipeline/summary/') })

export const useAgreement = (days: number) =>
  useQuery({ queryKey: ['agreement', days], queryFn: () => api<AgreementReport>(`/api/reports/agreement/?days=${days}`) })

// --- client portal
export const usePortalRequisitions = () =>
  useQuery({ queryKey: ['portal-reqs'], queryFn: () => api<PortalRequisition[]>('/api/portal/requisitions/') })

export const usePortalCandidates = (requisition?: string) =>
  useQuery({
    queryKey: ['portal-candidates', requisition ?? 'all'],
    queryFn: () => api<ClientCard[]>(`/api/portal/candidates/${qs({ requisition })}`),
  })

export const usePortalCandidate = (id: string) =>
  useQuery({ queryKey: ['portal-candidate', id], queryFn: () => api<ClientCard>(`/api/portal/candidates/${id}/`), staleTime: 30_000 })

export function usePortalActions(id: string) {
  const qc = useQueryClient()
  const done = (data: ClientCard) => {
    qc.setQueryData(['portal-candidate', id], data)
    qc.invalidateQueries({ queryKey: ['portal-candidates'] })
    qc.invalidateQueries({ queryKey: ['portal-reqs'] })
  }
  return {
    decide: useMutation({
      mutationFn: (v: { decision: 'shortlist' | 'reject'; reason?: string }) =>
        post<ClientCard>(`/api/portal/candidates/${id}/decision/`, v),
      onSuccess: done,
    }),
    propose: useMutation({
      mutationFn: (v: { starts_at: string; duration_minutes: number; note: string }) =>
        post<ClientCard>(`/api/portal/candidates/${id}/slots/`, v),
      onSuccess: done,
    }),
  }
}
