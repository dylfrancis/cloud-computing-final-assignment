import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { ApiError } from '../../api/client'
import { mlApi, type RetrainStatus } from '../../api/ml'
import { formatMoney } from '../../lib/format'
import styles from './HouseholdPredictions.module.css'

const PCT = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 })

export function HouseholdPredictions({ retrain }: { retrain: RetrainStatus | undefined }) {
  const [input, setInput] = useState('10')
  const [hshd, setHshd] = useState<number | null>(10)

  const enabled = hshd !== null && !!retrain && !retrain.is_training
  const queries = useQueries({
    queries: [
      {
        queryKey: ['ml', 'predict', 'clv', hshd],
        queryFn: () => mlApi.predictCLV(hshd!),
        enabled,
        retry: false,
      },
      {
        queryKey: ['ml', 'predict', 'churn', hshd],
        queryFn: () => mlApi.predictChurn(hshd!),
        enabled,
        retry: false,
      },
      {
        queryKey: ['ml', 'predict', 'basket', hshd],
        queryFn: () => mlApi.predictBasket(hshd!, 5),
        enabled,
        retry: false,
      },
    ],
  })
  const [clv, churn, basket] = queries

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const n = Number.parseInt(input, 10)
    if (Number.isFinite(n) && n > 0) setHshd(n)
  }

  const modelsNotReady =
    retrain &&
    !retrain.is_training &&
    (!retrain.models.clv.trained || !retrain.models.churn.trained || !retrain.models.basket.trained)

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>Household predictions</h3>
          <p className={styles.subtitle}>
            CLV, churn risk and basket recommendations for a single household.
          </p>
        </div>
        <form className={styles.form} onSubmit={submit}>
          <input
            className={styles.input}
            inputMode="numeric"
            pattern="[0-9]*"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="HSHD_NUM"
          />
          <button className={styles.submit} type="submit">
            Go
          </button>
        </form>
      </header>

      {retrain?.is_training && (
        <div className={styles.hint}>Models are training — predictions will be ready shortly.</div>
      )}
      {modelsNotReady && (
        <div className={styles.hint}>
          One or more models isn't trained yet. Click <em>Retrain all</em> above.
        </div>
      )}

      <div className={styles.grid}>
        <CLVCard query={clv} />
        <ChurnCard query={churn} />
        <BasketCard query={basket} />
      </div>
    </section>
  )
}

type QueryLike<T> = {
  data: T | undefined
  error: unknown
  isLoading: boolean
  isError: boolean
  fetchStatus: 'idle' | 'fetching' | 'paused'
}

function CLVCard({ query }: { query: QueryLike<Awaited<ReturnType<typeof mlApi.predictCLV>>> }) {
  return (
    <Tile title="Customer Lifetime Value" query={query}>
      {(data) => (
        <>
          <div className={styles.statValue}>{formatMoney(data.clv_score)}</div>
          <div className={styles.statRow}>
            <SegmentPill segment={data.segment} />
            <span className={styles.statMeta}>
              Top {PCT.format(1 - data.clv_percentile / 100)}
            </span>
          </div>
        </>
      )}
    </Tile>
  )
}

function ChurnCard({
  query,
}: {
  query: QueryLike<Awaited<ReturnType<typeof mlApi.predictChurn>>>
}) {
  return (
    <Tile title="Churn risk" query={query}>
      {(data) => (
        <>
          <div className={styles.statValue}>{PCT.format(data.churn_probability)}</div>
          <div className={styles.statRow}>
            <RiskPill level={data.risk_level} />
            <span className={styles.statMeta}>
              {data.is_churned ? 'Already churned' : 'Active'}
            </span>
          </div>
        </>
      )}
    </Tile>
  )
}

function BasketCard({
  query,
}: {
  query: QueryLike<Awaited<ReturnType<typeof mlApi.predictBasket>>>
}) {
  return (
    <Tile title="Basket recommendations" query={query} wide>
      {(data) =>
        data.recommendations.length === 0 ? (
          <div className={styles.statMeta}>No recommendations</div>
        ) : (
          <ul className={styles.recs}>
            {data.recommendations.map((rec) => (
              <li key={rec.product_id}>
                <span className={styles.recId}>Product #{rec.product_id}</span>
                <span className={styles.recMeta}>
                  Score {rec.score.toFixed(2)} · {rec.reason}
                </span>
              </li>
            ))}
          </ul>
        )
      }
    </Tile>
  )
}

function Tile<T>({
  title,
  query,
  wide,
  children,
}: {
  title: string
  query: QueryLike<T>
  wide?: boolean
  children: (data: T) => React.ReactNode
}) {
  return (
    <div className={`${styles.tile} ${wide ? styles.tileWide : ''}`}>
      <header className={styles.tileHeader}>{title}</header>
      {query.isLoading ? (
        <span className={styles.statMeta}>Loading…</span>
      ) : query.isError ? (
        <span className={styles.statMeta}>
          {query.error instanceof ApiError ? query.error.detail : 'Unavailable'}
        </span>
      ) : query.data ? (
        children(query.data)
      ) : (
        <span className={styles.statMeta}>No data</span>
      )}
    </div>
  )
}

function SegmentPill({ segment }: { segment: 'high' | 'medium' | 'low' }) {
  const cls =
    segment === 'high' ? styles.segHigh : segment === 'medium' ? styles.segMed : styles.segLow
  return <span className={`${styles.segPill} ${cls}`}>{segment}</span>
}

function RiskPill({ level }: { level: 'high' | 'medium' | 'low' }) {
  const cls = level === 'high' ? styles.segHigh : level === 'medium' ? styles.segMed : styles.segLow
  return <span className={`${styles.segPill} ${cls}`}>{level}</span>
}
