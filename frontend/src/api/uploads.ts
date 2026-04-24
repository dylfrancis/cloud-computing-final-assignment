import { ApiError } from './client'
import { getToken } from '../auth/storage'

export type UploadStage = 'queued' | 'unzipping' | 'loading' | 'retraining' | 'done'
export type UploadStatus = 'processing' | 'succeeded' | 'failed'

export type UploadJob = {
  job_id: string
  status: UploadStatus
  stage: UploadStage
  started_at: string
  finished_at: string | null
  counts: { households: number; products: number; transactions: number } | null
  dropped_transactions: number
  retrain: Record<string, string>
  error: string | null
}

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

// The typed client sets Content-Type: application/json which breaks multipart.
// This helper posts a FormData directly and parses the response.
export async function postUpload(form: FormData): Promise<UploadJob> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BASE_URL}/uploads`, { method: 'POST', headers, body: form })
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
  return res.json() as Promise<UploadJob>
}

export async function getUpload(jobId: string): Promise<UploadJob> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BASE_URL}/uploads/${jobId}`, { headers })
  if (!res.ok) throw new ApiError(res.status, res.statusText)
  return res.json() as Promise<UploadJob>
}
