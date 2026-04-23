import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { fetchHouseholdPull, type HouseholdPullResponse } from '../api/households'
import { ApiError } from '../api/client'
import { DataPullTable } from '../components/DataPullTable'
import styles from './Search.module.css'

const SAMPLE_HSHD = 10
const PAGE_SIZE = 200

export function Search() {
  const [input, setInput] = useState(String(SAMPLE_HSHD))
  const [submitted, setSubmitted] = useState<number | null>(SAMPLE_HSHD)
  const [offset, setOffset] = useState(0)

  const query = useQuery<HouseholdPullResponse, ApiError>({
    queryKey: ['householdPull', submitted, offset, PAGE_SIZE],
    queryFn: () => fetchHouseholdPull(submitted!, PAGE_SIZE, offset),
    enabled: submitted !== null,
    placeholderData: keepPreviousData,
    retry: (count, err) => err.status !== 404 && count < 2,
  })

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const n = Number.parseInt(input, 10)
    if (!Number.isFinite(n) || n <= 0) return
    setOffset(0)
    setSubmitted(n)
  }

  const page = offset / PAGE_SIZE + 1
  const pages = query.data ? Math.max(1, Math.ceil(query.data.total_rows / PAGE_SIZE)) : 1
  const canPrev = offset > 0
  const canNext = query.data ? offset + PAGE_SIZE < query.data.total_rows : false

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.title}>Household Data Pull</h2>
        <p className={styles.subtitle}>
          Enter an <code>HSHD_NUM</code> to view that household&apos;s transactions joined with
          product details, sorted by <code>Hshd_num, Basket_num, Date, Product_num, Department,
          Commodity</code>.
        </p>
      </header>

      <form className={styles.form} onSubmit={submit}>
        <label className={styles.label}>
          HSHD_NUM
          <input
            className={styles.input}
            inputMode="numeric"
            pattern="[0-9]*"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. 10"
          />
        </label>
        <button type="submit" className={styles.submit}>Search</button>
        <button
          type="button"
          className={styles.linkBtn}
          onClick={() => {
            setInput(String(SAMPLE_HSHD))
            setOffset(0)
            setSubmitted(SAMPLE_HSHD)
          }}
        >
          Sample (HSHD #{SAMPLE_HSHD})
        </button>
      </form>

      {query.isError && (
        <div className={styles.errorCard}>
          {query.error.status === 404
            ? `No household found for HSHD_NUM ${submitted}.`
            : `Request failed: ${query.error.detail}`}
        </div>
      )}

      {query.isLoading && <div className={styles.loadingCard}>Loading…</div>}

      {query.data && !query.isError && (
        <>
          <HouseholdHeader data={query.data} />
          <div className={styles.pager}>
            <span>
              Showing rows {query.data.total_rows === 0 ? 0 : offset + 1}–
              {Math.min(offset + PAGE_SIZE, query.data.total_rows)} of {query.data.total_rows}
              {' · '}page {page} / {pages}
            </span>
            <div className={styles.pagerButtons}>
              <button
                className={styles.pagerBtn}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={!canPrev || query.isFetching}
              >
                Prev
              </button>
              <button
                className={styles.pagerBtn}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={!canNext || query.isFetching}
              >
                Next
              </button>
            </div>
          </div>
          <DataPullTable rows={query.data.rows} />
        </>
      )}
    </section>
  )
}

function HouseholdHeader({ data }: { data: HouseholdPullResponse }) {
  const h = data.household
  const facts = [
    ['Loyalty', h.loyalty_flag],
    ['Age range', h.age_range],
    ['Marital', h.marital_status],
    ['Income', h.income_range],
    ['Homeowner', h.homeowner_desc],
    ['Composition', h.household_composition],
    ['Size', h.household_size],
    ['Children', h.children],
  ] as const
  return (
    <section className={styles.hhCard}>
      <h3 className={styles.hhTitle}>Household #{data.hshd_num}</h3>
      <dl className={styles.facts}>
        {facts.map(([k, v]) => (
          <div key={k} className={styles.factRow}>
            <dt>{k}</dt>
            <dd>{v ?? <span className={styles.muted}>—</span>}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
