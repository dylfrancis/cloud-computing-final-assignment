import type { ReactNode } from 'react'
import styles from './ChartCard.module.css'

export function ChartCard({
  title,
  subtitle,
  right,
  children,
}: {
  title: string
  subtitle?: string
  right?: ReactNode
  children: ReactNode
}) {
  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        {right && <div>{right}</div>}
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  )
}
