import { api } from './client'

export type TokenResponse = { access_token: string; token_type: string }

export type UserResponse = {
  id: number
  email: string
  username: string
  created_at: string
}

export function signup(email: string, username: string, password: string): Promise<TokenResponse> {
  return api<TokenResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, username, password }),
  })
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return api<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function getMe(): Promise<UserResponse> {
  return api<UserResponse>('/auth/me')
}
