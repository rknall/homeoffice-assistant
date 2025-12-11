// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { create } from 'zustand'
import { ApiError, api } from '@/api/client'
import type { AuthResponse, AuthStatus, User, UserPermissions } from '@/types'

interface AuthState {
  user: User | null
  isLoading: boolean
  isFirstRun: boolean | null
  registrationEnabled: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, fullName?: string) => Promise<void>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
  checkAuthStatus: () => Promise<void>
  clearError: () => void
  setUser: (user: User) => void
  hasPermission: (code: string, companyId?: string) => boolean
  fetchPermissions: () => Promise<void>
}

export const useAuth = create<AuthState>((set, get) => ({
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

  register: async (username: string, email: string, password: string, fullName?: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.post<AuthResponse>('/auth/register', {
        username,
        email,
        password,
        full_name: fullName || null,
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

  setUser: (user: User) => set({ user }),

  hasPermission: (code: string, companyId?: string) => {
    const user = get().user
    if (!user) return false

    // Check global permissions
    if (user.permissions.includes(code)) return true

    // Check company-specific permissions if companyId is provided
    if (companyId && user.company_permissions[companyId]?.includes(code)) return true

    return false
  },

  fetchPermissions: async () => {
    const user = get().user
    if (!user) return

    try {
      const userPermissions = await api.get<UserPermissions>('/rbac/me/permissions')
      set((state) => ({
        user: state.user ? {
          ...state.user,
          permissions: userPermissions.global_permissions,
          company_permissions: userPermissions.company_permissions,
        } : null,
      }))
    } catch (e) {
      console.error('Failed to fetch user permissions:', e)
      // Optionally clear permissions or set an error state
      set((state) => ({
        user: state.user ? {
          ...state.user,
          permissions: [],
          company_permissions: {},
        } : null,
      }))
    }
  },
}))
