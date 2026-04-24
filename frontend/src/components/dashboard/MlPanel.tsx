import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { mlApi, type ModelState } from '../../api/ml'
import styles from './MlPanel.module.css'

const MODELS = ['clv', 'churn', 'basket'] as const

const LABELS: Record<(typeof MODELS)[number], string> = {
  clv: 'Customer Lifetime Value',
  churn: 'Churn Risk',
  basket: 'Basket Analysis',
}

const PILL_LABEL: Record<string, string> = {
  pending: 'Untrained',
  running: 'Training…',
  ok: 'Trained',
  failed: 'Failed',
}

export function MlPanel() {
  const qc = useQueryClient()
  const status = useQuery({
    queryKey: ['ml', 'retrain'],
    queryFn: mlApi.retrainStatus,
    refetchInterval: (q) => (q.state.data?.is_training ? 2000 : false),
  })
  const start = useMutation({
    mutationFn: mlApi.startRetrain,
    onSuccess: (data) => qc.setQueryData(['ml', 'retrain'], data),
  })

  // Auto-kick training on first mount if no model has been trained yet and
  // we're not already training.
  const allUntrained =
    status.data &&
    !status.data.is_training &&
    MODELS.every((m) => !status.data!.models[m].trained)

  useEffect(() => {
    if (allUntrained && !start.isPending) start.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allUntrained])

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>ML models</h3>
          <p className={styles.subtitle}>
            CLV, churn and basket models retrain together.{' '}
            {status.data?.is_training
              ? 'Training in progress — this can take a few minutes.'
              : 'Retrain whenever the underlying data changes.'}
          </p>
        </div>
        <button
          type="button"
          className={styles.retrainBtn}
          disabled={status.data?.is_training || start.isPending}
          onClick={() => start.mutate()}
        >
          {status.data?.is_training ? 'Training…' : 'Retrain all'}
        </button>
      </header>

      <ul className={styles.models}>
        {MODELS.map((name) => {
          const m: ModelState | undefined = status.data?.models[name]
          const pill = m?.status ?? 'pending'
          return (
            <li key={name} className={styles.row}>
              <div className={styles.rowLeft}>
                <span className={styles.name}>{LABELS[name]}</span>
                {m?.training_date && (
                  <span className={styles.date}>
                    Last trained {new Date(m.training_date).toLocaleString()}
                  </span>
                )}
              </div>
              <span className={`${styles.pill} ${pillClass(pill, styles)}`}>
                {PILL_LABEL[pill] ?? pill}
              </span>
            </li>
          )
        })}
      </ul>

      {status.data &&
        MODELS.some((m) => status.data!.models[m].status === 'failed') && (
          <div className={styles.error}>
            {MODELS.filter((m) => status.data!.models[m].status === 'failed').map((m) => (
              <div key={m}>
                <strong>{LABELS[m]}:</strong> {status.data!.models[m].error}
              </div>
            ))}
          </div>
        )}
    </section>
  )
}

function pillClass(s: string, styles: Record<string, string>): string {
  if (s === 'ok') return styles.pillOk
  if (s === 'running') return styles.pillRunning
  if (s === 'failed') return styles.pillFail
  return styles.pillPending
}
