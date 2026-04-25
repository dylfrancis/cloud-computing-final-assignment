import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dashboardApi, type SpendPoint } from '../../api/dashboard'
import { formatMoney } from '../../lib/format'
import { ChartCard } from './ChartCard'
import styles from './SpendOverTimeChart.module.css'

const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const TICK = new Intl.DateTimeFormat('en-US', { month: 'short', year: '2-digit' })

function fmtBucket(raw: unknown): string {
  const s = String(raw ?? '')
  // Backend returns YYYY-MM-DD; tolerate a leading datetime ("YYYY-MM-DDT...")
  // by taking the date prefix.
  const datePart = s.length >= 10 ? s.slice(0, 10) : s
  const d = new Date(`${datePart}T00:00:00`)
  return Number.isFinite(d.getTime()) ? TICK.format(d) : s
}

export function SpendOverTimeChart() {
  const [grain, setGrain] = useState<'week' | 'month'>('week')
  const query = useQuery({
    queryKey: ['dashboard', 'spend-over-time', grain],
    queryFn: () => dashboardApi.spendOverTime(grain),
  })

  const data: SpendPoint[] = query.data?.points ?? []

  return (
    <ChartCard
      title="Spend over time"
      subtitle={`All-time, by ${grain}`}
      right={
        <div className={styles.toggle}>
          {(['week', 'month'] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGrain(g)}
              className={grain === g ? styles.toggleActive : styles.toggleBtn}
              type="button"
            >
              {g}
            </button>
          ))}
        </div>
      }
    >
      {query.isLoading ? (
        <Placeholder>Loading…</Placeholder>
      ) : query.isError ? (
        <Placeholder>Failed to load</Placeholder>
      ) : data.length === 0 ? (
        <Placeholder>No data</Placeholder>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              dataKey="bucket"
              stroke="var(--text)"
              fontSize={11}
              tickFormatter={(b) => fmtBucket(b)}
            />
            <YAxis
              stroke="var(--text)"
              fontSize={11}
              tickFormatter={(v) => `$${COMPACT.format(Number(v))}`}
              width={60}
            />
            <Tooltip
              formatter={(value) => [formatMoney(Number(value)), 'Spend']}
              labelFormatter={(l) => fmtBucket(l)}
              contentStyle={{
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="spend"
              stroke="var(--accent)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return <div className={styles.placeholder}>{children}</div>
}
