import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { dashboardApi } from '../../api/dashboard'
import { formatMoney } from '../../lib/format'
import { ChartCard } from './ChartCard'

const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

export function TopDepartmentsChart() {
  const query = useQuery({
    queryKey: ['dashboard', 'top-departments'],
    queryFn: () => dashboardApi.topDepartments(10),
  })

  return (
    <ChartCard title="Top departments" subtitle="By total spend, all time">
      {query.isLoading ? (
        <Placeholder>Loading…</Placeholder>
      ) : query.isError ? (
        <Placeholder>Failed to load</Placeholder>
      ) : !query.data || query.data.items.length === 0 ? (
        <Placeholder>No data</Placeholder>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={query.data.items}
            layout="vertical"
            margin={{ top: 4, right: 16, bottom: 0, left: 80 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis
              type="number"
              stroke="var(--text)"
              fontSize={11}
              tickFormatter={(v) => `$${COMPACT.format(Number(v))}`}
            />
            <YAxis
              dataKey="department"
              type="category"
              stroke="var(--text)"
              fontSize={11}
              width={80}
            />
            <Tooltip
              formatter={(value) => [formatMoney(Number(value)), 'Spend']}
              contentStyle={{
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <Bar dataKey="spend" fill="var(--accent)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  )
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text)',
        fontSize: 13,
      }}
    >
      {children}
    </div>
  )
}
