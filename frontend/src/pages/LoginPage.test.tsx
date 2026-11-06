import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'

type Reply = { status: number; body?: unknown }

/** Fake the Django API by path; anything unlisted is a 403 like an anonymous session. */
function mockApi(routes: Record<string, Reply>) {
  const fetchMock = vi.fn(async (url: string) => {
    const r = routes[url] ?? { status: 403, body: { detail: 'Authentication credentials were not provided.' } }
    return new Response(r.status === 204 ? null : JSON.stringify(r.body ?? {}), { status: r.status })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function renderApp(path = '/login') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const user = (role: string, extra = {}) => ({ id: 1, email: 'u@example.com', full_name: 'Test User', role, client_org: null, ...extra })

afterEach(() => vi.unstubAllGlobals())

describe('login page', () => {
  it('shows validation errors and does not call the API', async () => {
    const fetchMock = mockApi({})
    renderApp()
    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter your email')).toBeInTheDocument()
    expect(screen.getByText('Enter your password')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/login/', expect.anything())
  })

  it('shows the server error for bad credentials', async () => {
    mockApi({
      '/api/auth/csrf/': { status: 200 },
      '/api/auth/login/': { status: 400, body: { detail: 'Invalid email or password.' } },
    })
    renderApp()
    await userEvent.type(await screen.findByLabelText('Email'), 'a@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
  })

  it.each([
    ['recruiter', 'Requisitions'],
    ['delivery_head', 'Delivery'],
    ['client', 'Your shortlist'],
  ])('sends a %s to their own home', async (role, heading) => {
    mockApi({ '/api/auth/csrf/': { status: 200 }, '/api/auth/login/': { status: 200, body: user(role) } })
    renderApp()
    await userEvent.type(await screen.findByLabelText('Email'), 'u@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
  })
})

describe('route guards', () => {
  it('sends a signed-out visitor to login', async () => {
    mockApi({})
    renderApp('/requisitions')
    expect(await screen.findByText('Sign in to FairRank')).toBeInTheDocument()
  })

  it("bounces a client away from the recruiter's page", async () => {
    mockApi({ '/api/auth/me/': { status: 200, body: user('client', { client_org: { id: 1, name: 'Org A' } }) } })
    renderApp('/requisitions')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Your shortlist' })).toBeInTheDocument())
  })
})
