import type { PullRow } from '../api/households'
import { formatDate, formatMoney } from '../lib/format'
import styles from './DataPullTable.module.css'

export function DataPullTable({ rows }: { rows: PullRow[] }) {
  if (rows.length === 0) {
    return <div className={styles.empty}>No transactions for this household.</div>
  }
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Basket</th>
            <th>Date</th>
            <th>Product</th>
            <th>Department</th>
            <th>Commodity</th>
            <th>Brand</th>
            <th>Organic</th>
            <th className={styles.num}>Spend</th>
            <th className={styles.num}>Units</th>
            <th>Region</th>
            <th className={styles.num}>Week</th>
            <th className={styles.num}>Year</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={`${r.basket_num}-${r.product_num}-${i}`}>
              <td>{r.basket_num}</td>
              <td>{formatDate(r.purchase_date)}</td>
              <td className={styles.mono}>{r.product_num}</td>
              <td>{r.department ?? '—'}</td>
              <td>{r.commodity ?? '—'}</td>
              <td>{r.brand_type ?? '—'}</td>
              <td>{r.natural_organic_flag ?? '—'}</td>
              <td className={styles.num}>{formatMoney(r.spend)}</td>
              <td className={styles.num}>{r.units}</td>
              <td>{r.store_region ?? '—'}</td>
              <td className={styles.num}>{r.week_num ?? '—'}</td>
              <td className={styles.num}>{r.year ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
