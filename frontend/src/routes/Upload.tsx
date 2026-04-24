import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getUpload, postUpload, type UploadJob } from '../api/uploads'
import styles from './Upload.module.css'

type Mode = 'archive' | 'csvs'

const STAGE_LABEL: Record<UploadJob['stage'], string> = {
  queued: 'Queued',
  unzipping: 'Unzipping',
  loading: 'Loading into database',
  retraining: 'Retraining ML models',
  done: 'Done',
}

export function Upload() {
  const [mode, setMode] = useState<Mode>('archive')
  const [archive, setArchive] = useState<File | null>(null)
  const [households, setHouseholds] = useState<File | null>(null)
  const [products, setProducts] = useState<File | null>(null)
  const [transactions, setTransactions] = useState<File | null>(null)
  const [job, setJob] = useState<UploadJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }, [])

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  function startPolling(jobId: string) {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const next = await getUpload(jobId)
        setJob(next)
        if (next.status !== 'processing') stopPolling()
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : 'Polling failed')
        stopPolling()
      }
    }, 2000)
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    const form = new FormData()
    if (mode === 'archive') {
      if (!archive) {
        setError('Select a zip file.')
        return
      }
      form.append('archive', archive)
    } else {
      if (!households && !products && !transactions) {
        setError('Select at least one CSV.')
        return
      }
      if (households) form.append('households', households)
      if (products) form.append('products', products)
      if (transactions) form.append('transactions', transactions)
    }

    setBusy(true)
    try {
      const created = await postUpload(form)
      setJob(created)
      startPolling(created.job_id)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  const processing = job?.status === 'processing'

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.title}>Upload new data</h2>
        <p className={styles.subtitle}>
          Replace the households, products, and transactions tables. ML models are retrained
          automatically after a successful load.
        </p>
      </header>

      <div className={styles.modeToggle}>
        <button
          className={mode === 'archive' ? styles.modeActive : styles.modeBtn}
          onClick={() => setMode('archive')}
          type="button"
          disabled={processing}
        >
          Zip archive
        </button>
        <button
          className={mode === 'csvs' ? styles.modeActive : styles.modeBtn}
          onClick={() => setMode('csvs')}
          type="button"
          disabled={processing}
        >
          Individual CSVs
        </button>
      </div>

      <form className={styles.form} onSubmit={submit}>
        {mode === 'archive' ? (
          <FileField
            label="Archive (.zip)"
            accept=".zip,application/zip"
            file={archive}
            onChange={setArchive}
            disabled={processing}
          />
        ) : (
          <>
            <p className={styles.note}>
              Transactions reference households and products via FKs. Any upload that replaces
              households or products will also clear the transactions table — include a
              transactions.csv if you want rows to remain.
            </p>
            <FileField
              label="Households (.csv)"
              accept=".csv,text/csv"
              file={households}
              onChange={setHouseholds}
              disabled={processing}
            />
            <FileField
              label="Products (.csv)"
              accept=".csv,text/csv"
              file={products}
              onChange={setProducts}
              disabled={processing}
            />
            <FileField
              label="Transactions (.csv)"
              accept=".csv,text/csv"
              file={transactions}
              onChange={setTransactions}
              disabled={processing}
            />
          </>
        )}

        {error && <div className={styles.error}>{error}</div>}

        <button className={styles.submit} type="submit" disabled={busy || processing}>
          {busy ? 'Uploading…' : processing ? 'Job running…' : 'Upload'}
        </button>
      </form>

      {job && <JobPanel job={job} />}
    </section>
  )
}

function retrainLabel(result: string): string {
  if (result === 'ok') return 'Trained'
  if (result === 'running') return 'Training…'
  if (result === 'pending') return 'Pending'
  return result // "failed: <reason>"
}

function retrainClass(result: string, s: Record<string, string>): string {
  if (result === 'ok') return s.retrainOk
  if (result === 'running') return s.retrainRunning
  if (result === 'pending') return s.retrainPending
  return s.retrainFail
}

function FileField({
  label,
  accept,
  file,
  onChange,
  disabled,
}: {
  label: string
  accept: string
  file: File | null
  onChange: (f: File | null) => void
  disabled?: boolean
}) {
  return (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{label}</span>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        disabled={disabled}
      />
      {file && (
        <span className={styles.fileMeta}>
          {file.name} · {(file.size / (1024 * 1024)).toFixed(2)} MB
        </span>
      )}
    </label>
  )
}

function JobPanel({ job }: { job: UploadJob }) {
  const statusClass =
    job.status === 'succeeded'
      ? styles.statusOk
      : job.status === 'failed'
        ? styles.statusFail
        : styles.statusBusy
  return (
    <section className={styles.jobCard}>
      <header className={styles.jobHeader}>
        <h3>Job {job.job_id.slice(0, 8)}</h3>
        <span className={`${styles.statusPill} ${statusClass}`}>{job.status}</span>
      </header>

      <div className={styles.stageRow}>
        <span className={styles.stageLabel}>Stage</span>
        <span>{STAGE_LABEL[job.stage]}</span>
      </div>

      {job.counts && (
        <dl className={styles.counts}>
          <div>
            <dt>Households</dt>
            <dd>{job.counts.households.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Products</dt>
            <dd>{job.counts.products.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Transactions</dt>
            <dd>
              {job.counts.transactions.toLocaleString()}
              {job.dropped_transactions > 0 && (
                <span className={styles.muted}>
                  {' '}
                  · {job.dropped_transactions.toLocaleString()} dropped (unknown FK)
                </span>
              )}
            </dd>
          </div>
        </dl>
      )}

      {Object.keys(job.retrain).length > 0 && (
        <section className={styles.retrain}>
          <h4>ML retrain</h4>
          <ul className={styles.retrainList}>
            {Object.entries(job.retrain).map(([name, result]) => (
              <li key={name} className={styles.retrainRow}>
                <span className={styles.retrainName}>{name}</span>
                <span className={`${styles.retrainPill} ${retrainClass(result, styles)}`}>
                  {retrainLabel(result)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {job.error && <div className={styles.error}>{job.error}</div>}
    </section>
  )
}
