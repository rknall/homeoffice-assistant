// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { create } from 'zustand'
import { api, errorMessage } from '@/api/client'
import type { Company } from '@/types'

interface CompaniesState {
  companies: Company[]
  isLoading: boolean
  error: string | null
  /** Reload the list; on failure the previous list is kept and `error` is set. */
  fetchCompanies: () => Promise<void>
}

export const useCompanies = create<CompaniesState>((set) => ({
  companies: [],
  isLoading: true,
  error: null,

  fetchCompanies: async () => {
    try {
      const companies = await api.get<Company[]>('/companies')
      set({ companies, error: null, isLoading: false })
    } catch (e) {
      set({ error: errorMessage(e, 'Failed to load companies'), isLoading: false })
    }
  },
}))
