/** Thin API client with bearer-token auth and transparent refresh. */

const API_BASE = '/api'

type Tokens = { access_token: string; refresh_token: string } | null

let tokensCache: Tokens = (() => {
  try {
    const raw = localStorage.getItem('maparr.tokens')
    return raw ? (JSON.parse(raw) as Tokens) : null
  } catch {
    return null
  }
})()

const listeners = new Set<() => void>()

export function getTokens(): Tokens {
  return tokensCache
}

export function setTokens(tokens: Tokens): void {
  tokensCache = tokens
  try {
    if (tokens) localStorage.setItem('maparr.tokens', JSON.stringify(tokens))
    else localStorage.removeItem('maparr.tokens')
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => {
    try {
      l()
    } catch {
      /* ignore */
    }
  })
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

let refreshing: Promise<string> | null = null

async function refreshAccess(): Promise<string> {
  const tokens = getTokens()
  if (!tokens?.refresh_token) throw new Error('not authenticated')
  if (!refreshing) {
    refreshing = (async () => {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: tokens.refresh_token }),
      })
      if (!res.ok) throw new Error('token refresh failed')
    const data = (await res.json()) as Tokens
    if (!data) throw new Error('Invalid token response')
    setTokens({ access_token: data.access_token, refresh_token: data.refresh_token })
    return data.access_token
    })()
  }
  try {
    return await refreshing
  } finally {
    refreshing = null
  }
}

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  query?: Record<string, string | number | boolean | undefined>
  raw?: boolean
}

export async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = new URL(path, window.location.origin)
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v === undefined || v === null || v === '') continue
      url.searchParams.set(k, String(v))
    }
  }

  const headers: Record<string, string> = {
    Accept: opts.raw ? 'application/octet-stream' : 'application/json',
    ...(opts.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...opts.headers,
  }

  const tokens = getTokens()
  if (tokens?.access_token) headers.Authorization = `Bearer ${tokens.access_token}`

  const doFetch = async (): Promise<Response> => {
    return fetch(url.toString(), {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    })
  }

  let res = await doFetch()

  if (res.status === 401 && getTokens()?.refresh_token) {
    try {
      await refreshAccess()
      headers.Authorization = `Bearer ${getTokens()?.access_token}`
      res = await doFetch()
    } catch {
      setTokens(null)
      throw new ApiError(401, 'Session expired. Please log in again.')
    }
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      if (typeof data?.detail === 'string') detail = data.detail
      else if (data?.detail) detail = JSON.stringify(data.detail)
      else if (data?.message) detail = data.message
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  if (opts.raw) return (await res.blob()) as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query']) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}