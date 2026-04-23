import { api } from './client'

export type HouseholdSummary = {
  hshd_num: number
  loyalty_flag: string | null
  age_range: string | null
  marital_status: string | null
  income_range: string | null
  homeowner_desc: string | null
  household_composition: string | null
  household_size: string | null
  children: string | null
}

export type PullRow = {
  basket_num: number
  purchase_date: string
  product_num: number
  department: string | null
  commodity: string | null
  brand_type: string | null
  natural_organic_flag: string | null
  spend: number
  units: number
  store_region: string | null
  week_num: number | null
  year: number | null
}

export type HouseholdPullResponse = {
  hshd_num: number
  household: HouseholdSummary
  total_rows: number
  limit: number
  offset: number
  rows: PullRow[]
}

export function fetchHouseholdPull(
  hshdNum: number,
  limit: number,
  offset: number,
): Promise<HouseholdPullResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return api<HouseholdPullResponse>(`/households/${hshdNum}/pull?${params}`)
}
