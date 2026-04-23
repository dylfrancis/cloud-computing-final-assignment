const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`)
    this.status = status
    this.detail = detail
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}
