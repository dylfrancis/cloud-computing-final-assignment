import { api } from './client'

export type Kpis = {
  total_spend: number
  total_units: number
  transactions: number
  unique_households: number
  unique_products: number
  unique_baskets: number
  avg_basket_spend: number
}

export type SpendPoint = {
  bucket: string
  spend: number
  transactions: number
}

export type SpendOverTime = {
  grain: 'week' | 'month'
  points: SpendPoint[]
}

export type CategoryShare = {
  label: string
  spend: number
  transactions: number
  share: number
}

export type CategoryShareList = {
  total_spend: number
  items: CategoryShare[]
}

export type DepartmentSpend = {
  department: string
  spend: number
  transactions: number
}

export type TopDepartments = {
  items: DepartmentSpend[]
}

export const dashboardApi = {
  kpis: () => api<Kpis>('/dashboard/kpis'),
  spendOverTime: (grain: 'week' | 'month' = 'week') =>
    api<SpendOverTime>(`/dashboard/spend-over-time?grain=${grain}`),
  topDepartments: (limit = 10) =>
    api<TopDepartments>(`/dashboard/top-departments?limit=${limit}`),
  brandMix: () => api<CategoryShareList>('/dashboard/brand-mix'),
  organicMix: () => api<CategoryShareList>('/dashboard/organic-mix'),
}
