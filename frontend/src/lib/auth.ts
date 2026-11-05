import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '@/lib/api'

export type Role = 'recruiter' | 'client' | 'delivery_head'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  client_org: { id: number; name: string } | null
}

/** Where each role lands after login. */
export function homeFor(role: Role): string {
  switch (role) {
    case 'recruiter':
      return '/requisitions'
    case 'delivery_head':
      return '/pipeline'
    case 'client':
      return '/portal'
  }
}

export const ME_KEY = ['me'] as const

/** The signed-in user, or null when there is no session (403 from the API). */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    retry: false,
    staleTime: 60_000,
    queryFn: async () => {
      try {
        return await api<User>('/api/auth/me/')
      } catch (e) {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null
        throw e
      }
    },
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      await api('/api/auth/csrf/') // sets the csrftoken cookie
      return api<User>('/api/auth/login/', { method: 'POST', body: creds })
    },
    onSuccess: (user) => qc.setQueryData(ME_KEY, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api<void>('/api/auth/logout/', { method: 'POST' }),
    onSuccess: () => {
      qc.clear()
      qc.setQueryData(ME_KEY, null)
    },
  })
}
