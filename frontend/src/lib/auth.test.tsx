import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'

afterEach(() => vi.unstubAllGlobals())

describe('sign out', () => {
  it('leaves the signed-in page at once and shows the login screen (no stale data under a signed-out session)', async () => {
    let signedIn = true
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url === '/api/auth/logout/') {
          signedIn = false
          return new Response(null, { status: 204 })
        }
        if (!signedIn) return new Response('{}', { status: 403 })
        if (url === '/api/auth/me/') return new Response(JSON.stringify({ id: 1, email: 'r@x.example', full_name: 'Asha Verma', role: 'recruiter', client_org: null }), { status: 200 })
        if (url === '/api/requisitions/' && (!init || !init.method || init.method === 'GET')) return new Response('[]', { status: 200 })
        if (url === '/api/client-orgs/') return new Response('[]', { status: 200 })
        return new Response('{}', { status: 404 })
      }),
    )
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={['/requisitions']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await userEvent.click(await screen.findByRole('button', { name: /account|AV|Asha/i }))
    await userEvent.click(await screen.findByRole('menuitem', { name: /sign out/i }))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Requisitions' })).toBeNull()
  })
})
