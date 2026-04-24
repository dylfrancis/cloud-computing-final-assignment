import { useEffect, useState, type ReactNode } from 'react'
import { getMe, login as apiLogin, signup as apiSignup, type UserResponse } from '../api/auth'
import { AuthContext } from './context'
import { clearToken, getToken, setToken } from './storage'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  // If there is no token we are trivially "loaded" with no user.
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    let cancelled = false
    getMe()
      .then((u) => {
        if (!cancelled) setUser(u)
      })
      .catch(() => clearToken())
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function login(email: string, password: string) {
    const { access_token } = await apiLogin(email, password)
    setToken(access_token)
    setUser(await getMe())
  }

  async function signup(email: string, username: string, password: string) {
    const { access_token } = await apiSignup(email, username, password)
    setToken(access_token)
    setUser(await getMe())
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
