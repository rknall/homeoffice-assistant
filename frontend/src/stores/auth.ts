import { create } from 'zustand'
import { api, ApiError } from '@/api/client'
import type { AuthResponse, AuthStatus, User } from '@/types'

interface AuthState {
  user: User | null
  isLoading: boolean
  isFirstRun: boolean | null
  registrationEnabled: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
  checkAuthStatus: () => Promise<void>
  clearError: () => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isFirstRun: null,
  registrationEnabled: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.post<AuthResponse>('/auth/login', { username, password })
      set({ user: response.user, isLoading: false })
    } catch (e) {
      const error = e instanceof ApiError ? e.message : 'Login failed'
      set({ error, isLoading: false })
      throw e
    }
  },

  register: async (username: string, email: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.post<AuthResponse>('/auth/register', {
        username,
        email,
        password,
      })
      set({ user: response.user, isLoading: false, isFirstRun: false })
    } catch (e) {
      const error = e instanceof ApiError ? e.message : 'Registration failed'
      set({ error, isLoading: false })
      throw e
    }
  },

  logout: async () => {
    set({ isLoading: true })
    try {
      await api.post('/auth/logout')
    } finally {
      set({ user: null, isLoading: false })
    }
  },

  checkSession: async () => {
    set({ isLoading: true })
    try {
      const response = await api.get<AuthResponse>('/auth/me')
      set({ user: response.user, isLoading: false })
    } catch {
      set({ user: null, isLoading: false })
    }
  },

  checkAuthStatus: async () => {
    try {
      const status = await api.get<AuthStatus>('/auth/status')
      set({
        isFirstRun: status.first_run,
        registrationEnabled: status.registration_enabled,
      })
    } catch {
      set({ isFirstRun: false, registrationEnabled: false })
    }
  },

  clearError: () => set({ error: null }),
}))
