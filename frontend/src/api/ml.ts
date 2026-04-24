import { api } from './client'

export type ModelName = 'clv' | 'churn' | 'basket'
export type ModelStatus = 'pending' | 'running' | 'ok' | 'failed'

export type ModelState = {
  status: ModelStatus
  trained: boolean
  training_date: string | null
  error: string | null
}

export type RetrainStatus = {
  is_training: boolean
  models: Record<ModelName, ModelState>
}

export type CLVPrediction = {
  hshd_num: number
  clv_score: number
  clv_percentile: number
  segment: 'high' | 'medium' | 'low'
}

export type ChurnPrediction = {
  hshd_num: number
  churn_probability: number
  risk_level: 'high' | 'medium' | 'low'
  is_churned: boolean
}

export type ProductRecommendation = {
  product_id: number
  score: number
  reason: string
}

export type BasketPrediction = {
  hshd_num: number
  recommendations: ProductRecommendation[]
}

export const mlApi = {
  retrainStatus: () => api<RetrainStatus>('/ml/retrain'),
  startRetrain: () => api<RetrainStatus>('/ml/retrain', { method: 'POST' }),
  predictCLV: (hshd: number) => api<CLVPrediction>(`/ml/predict/clv/${hshd}`),
  predictChurn: (hshd: number) => api<ChurnPrediction>(`/ml/predict/churn/${hshd}`),
  predictBasket: (hshd: number, limit = 5) =>
    api<BasketPrediction>(`/ml/predict/basket/${hshd}?limit=${limit}`),
}
