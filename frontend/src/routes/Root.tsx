import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import styles from './Root.module.css'

export function Root() {
  const { user, logout } = useAuth()
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.brand}>Retail Insights</h1>
        <nav className={styles.nav}>
          <NavLink to="/" end className={navClass}>Search</NavLink>
          <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>
          <NavLink to="/upload" className={navClass}>Upload</NavLink>
        </nav>
        <div className={styles.user}>
          {user ? (
            <>
              <span className={styles.userEmail}>{user.email}</span>
              <button className={styles.logout} onClick={logout}>Sign out</button>
            </>
          ) : null}
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? `${styles.link} ${styles.linkActive}` : styles.link
}
