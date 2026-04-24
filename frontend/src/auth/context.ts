import { createContext } from 'react'
import type { UserResponse } from '../api/auth'

export type AuthContextValue = {
  user: UserResponse | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
