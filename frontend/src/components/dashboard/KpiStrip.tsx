import type { Kpis } from '../../api/dashboard'
import { formatMoney } from '../../lib/format'
import styles from './KpiStrip.module.css'

const FMT_INT = new Intl.NumberFormat('en-US')

export function KpiStrip({ data }: { data: Kpis }) {
  const items = [
    { label: 'Total spend', value: formatMoney(data.total_spend) },
    { label: 'Transactions', value: FMT_INT.format(data.transactions) },
    { label: 'Households', value: FMT_INT.format(data.unique_households) },
    { label: 'Products', value: FMT_INT.format(data.unique_products) },
    { label: 'Baskets', value: FMT_INT.format(data.unique_baskets) },
    { label: 'Avg basket', value: formatMoney(data.avg_basket_spend) },
  ] as const

  return (
    <section className={styles.strip}>
      {items.map((it) => (
        <div key={it.label} className={styles.card}>
          <span className={styles.label}>{it.label}</span>
          <span className={styles.value}>{it.value}</span>
        </div>
      ))}
    </section>
  )
}
