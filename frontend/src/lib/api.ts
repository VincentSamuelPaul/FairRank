export class ApiError extends Error {
  status: number
  fields: Record<string, string>
  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

function cookie(name: string): string | undefined {
  return document.cookie
    .split('; ')
    .find((c) => c.startsWith(`${name}=`))
    ?.slice(name.length + 1)
}

const SAFE = new Set(['GET', 'HEAD', 'OPTIONS'])

/** DRF error bodies are {detail} or {field: [messages]}; flatten them into one readable message. */
function readError(data: unknown): { message: string; fields: Record<string, string> } {
  const fallback = 'Something went wrong. Please try again.'
  if (!data || typeof data !== 'object') return { message: fallback, fields: {} }
  const body = data as Record<string, unknown>
  if (typeof body.detail === 'string') return { message: body.detail, fields: {} }
  const fields: Record<string, string> = {}
  for (const [key, value] of Object.entries(body)) {
    const first = Array.isArray(value) ? value[0] : value
    if (typeof first === 'string') fields[key] = first
  }
  const message = Object.values(fields)[0] ?? fallback
  return { message, fields }
}

interface Init {
  method?: string
  body?: unknown
  form?: FormData
}

/** Same-origin JSON client. Sends the session cookie and echoes the CSRF cookie on unsafe methods. */
export async function api<T>(path: string, init: Init = {}): Promise<T> {
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
    body: init.form ?? (init.body !== undefined ? JSON.stringify(init.body) : undefined),
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const { message, fields } = readError(data)
    throw new ApiError(res.status, message, fields)
  }
  return data as T
}

export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body })
