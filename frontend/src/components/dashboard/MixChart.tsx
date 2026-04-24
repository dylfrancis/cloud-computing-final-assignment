import { useQuery } from '@tanstack/react-query'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { CategoryShareList } from '../../api/dashboard'
import { formatMoney } from '../../lib/format'
import { ChartCard } from './ChartCard'

const COLORS = ['#aa3bff', '#7c3aed', '#6366f1', '#ec4899', '#f97316', '#64748b']
const PCT = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 })

export function MixChart({
  title,
  subtitle,
  queryKey,
  fetcher,
}: {
  title: string
  subtitle?: string
  queryKey: readonly unknown[]
  fetcher: () => Promise<CategoryShareList>
}) {
  const query = useQuery({ queryKey, queryFn: fetcher })

  return (
    <ChartCard title={title} subtitle={subtitle}>
      {query.isLoading ? (
        <Placeholder>Loading…</Placeholder>
      ) : query.isError ? (
        <Placeholder>Failed to load</Placeholder>
      ) : !query.data || query.data.items.length === 0 ? (
        <Placeholder>No data</Placeholder>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={query.data.items}
                dataKey="spend"
                nameKey="label"
                innerRadius={52}
                outerRadius={80}
                paddingAngle={2}
                stroke="var(--bg)"
              >
                {query.data.items.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [formatMoney(Number(v)), 'Spend']}
                contentStyle={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul
            style={{
              listStyle: 'none',
              margin: 0,
              padding: 0,
              alignSelf: 'center',
              fontSize: 13,
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            {query.data.items.map((it, i) => (
              <li
                key={it.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  color: 'var(--text-h)',
                }}
              >
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 2,
                    background: COLORS[i % COLORS.length],
                  }}
                />
                <span style={{ flex: 1 }}>{it.label}</span>
                <span style={{ color: 'var(--text)' }}>{PCT.format(it.share)}</span>
              </li>
            ))}
          </ul>
        </div>
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
