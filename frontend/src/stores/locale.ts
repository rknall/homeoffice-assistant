// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { create } from 'zustand'
import { api } from '@/api/client'
import type { LocaleSettings, DateFormatType, TimeFormatType } from '@/types'

interface LocaleState {
  settings: LocaleSettings
  isLoading: boolean
  isLoaded: boolean
  fetchSettings: () => Promise<void>
  updateSettings: (settings: Partial<LocaleSettings>) => Promise<void>
  formatDate: (date: string | Date) => string
  formatTime: (time: string | Date) => string
  formatDateTime: (datetime: string | Date) => string
}

const defaultSettings: LocaleSettings = {
  date_format: 'YYYY-MM-DD',
  time_format: '24h',
  timezone: 'UTC',
}

// Format date according to settings
function formatDateString(date: Date, format: DateFormatType): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  switch (format) {
    case 'DD.MM.YYYY':
      return `${day}.${month}.${year}`
    case 'DD/MM/YYYY':
      return `${day}/${month}/${year}`
    case 'MM/DD/YYYY':
      return `${month}/${day}/${year}`
    case 'YYYY-MM-DD':
    default:
      return `${year}-${month}-${day}`
  }
}

// Format time according to settings
function formatTimeString(date: Date, format: TimeFormatType): string {
  const hours24 = date.getHours()
  const minutes = String(date.getMinutes()).padStart(2, '0')

  if (format === '12h') {
    const hours12 = hours24 % 12 || 12
    const period = hours24 < 12 ? 'AM' : 'PM'
    return `${hours12}:${minutes} ${period}`
  }

  return `${String(hours24).padStart(2, '0')}:${minutes}`
}

export const useLocale = create<LocaleState>((set, get) => ({
  settings: defaultSettings,
  isLoading: false,
  isLoaded: false,

  fetchSettings: async () => {
    set({ isLoading: true })
    try {
      const settings = await api.get<LocaleSettings>('/settings/locale')
      set({ settings, isLoaded: true })
    } catch {
      // Use defaults if fetch fails
      set({ settings: defaultSettings, isLoaded: true })
    } finally {
      set({ isLoading: false })
    }
  },

  updateSettings: async (newSettings: Partial<LocaleSettings>) => {
    const settings = await api.put<LocaleSettings>('/settings/locale', newSettings)
    set({ settings })
  },

  formatDate: (date: string | Date) => {
    const { settings } = get()
    const dateObj = typeof date === 'string' ? new Date(date) : date
    return formatDateString(dateObj, settings.date_format)
  },

  formatTime: (time: string | Date) => {
    const { settings } = get()
    const dateObj = typeof time === 'string' ? new Date(time) : time
    return formatTimeString(dateObj, settings.time_format)
  },

  formatDateTime: (datetime: string | Date) => {
    const { settings } = get()
    const dateObj = typeof datetime === 'string' ? new Date(datetime) : datetime
    return `${formatDateString(dateObj, settings.date_format)} ${formatTimeString(dateObj, settings.time_format)}`
  },
}))
