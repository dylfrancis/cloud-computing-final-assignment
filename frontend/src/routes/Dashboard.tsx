import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboard'
import { mlApi } from '../api/ml'
import { HouseholdPredictions } from '../components/dashboard/HouseholdPredictions'
import { KpiStrip } from '../components/dashboard/KpiStrip'
import { MixChart } from '../components/dashboard/MixChart'
import { MlPanel } from '../components/dashboard/MlPanel'
import { SpendOverTimeChart } from '../components/dashboard/SpendOverTimeChart'
import { TopDepartmentsChart } from '../components/dashboard/TopDepartmentsChart'
import styles from './Dashboard.module.css'

export function Dashboard() {
  const kpis = useQuery({ queryKey: ['dashboard', 'kpis'], queryFn: dashboardApi.kpis })
  const retrain = useQuery({
    queryKey: ['ml', 'retrain'],
    queryFn: mlApi.retrainStatus,
    refetchInterval: (q) => (q.state.data?.is_training ? 2000 : false),
  })

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.title}>Dashboard</h2>
        <p className={styles.subtitle}>
          All-time spend, category mix, and ML predictions over the 84.51° sample.
        </p>
      </header>

      {kpis.data ? (
        <KpiStrip data={kpis.data} />
      ) : (
        <div className={styles.kpiPlaceholder}>
          {kpis.isError ? 'Failed to load KPIs.' : 'Loading KPIs…'}
        </div>
      )}

      <div className={styles.grid}>
        <SpendOverTimeChart />
        <TopDepartmentsChart />
        <MixChart
          title="Brand mix"
          subtitle="Private vs national label, by spend"
          queryKey={['dashboard', 'brand-mix']}
          fetcher={dashboardApi.brandMix}
        />
        <MixChart
          title="Natural / Organic mix"
          subtitle="Share of spend"
          queryKey={['dashboard', 'organic-mix']}
          fetcher={dashboardApi.organicMix}
        />
      </div>

      <div className={styles.mlStack}>
        <MlPanel />
        <HouseholdPredictions retrain={retrain.data} />
      </div>
    </section>
  )
}
