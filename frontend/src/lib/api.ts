export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function cookie(name: string): string | undefined {
  return document.cookie
    .split('; ')
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1)
}

const SAFE = new Set(['GET', 'HEAD', 'OPTIONS'])

/** Same-origin JSON client. Sends the session cookie and echoes the CSRF cookie on unsafe methods. */
export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (init.body !== undefined) headers['Content-Type'] = 'application/json'
  if (!SAFE.has(method)) {
    const token = cookie('csrftoken')
    if (token) headers['X-CSRFToken'] = token
  }
  const res = await fetch(path, {
    method,
    headers,
    credentials: 'same-origin',
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, data.detail ?? 'Something went wrong. Please try again.')
  return data as T
}
