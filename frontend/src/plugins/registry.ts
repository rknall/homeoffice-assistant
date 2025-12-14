// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { create } from 'zustand'
import { api } from '@/api/client'
import { pluginLoader } from './loader'
import type {
  DiscoveredPlugin,
  DiscoveredPluginsResponse,
  LoadedPlugin,
  PluginEnableResponse,
  PluginInfo,
  PluginInstallResponse,
  PluginListResponse,
  PluginNavItem,
  PluginRoute,
  PluginSettingsResponse,
  PluginSummary,
  PluginUninstallResponse,
} from './types'

interface PluginsState {
  // Plugin data
  plugins: PluginSummary[]
  discoveredPlugins: DiscoveredPlugin[]
  loadedPlugins: LoadedPlugin[]

  // Loading state
  isLoading: boolean
  isInitialized: boolean
  error: string | null

  // Actions
  fetchPlugins: () => Promise<void>
  fetchDiscoveredPlugins: () => Promise<void>
  loadAllFrontends: () => Promise<void>
  getPluginInfo: (pluginId: string) => Promise<PluginInfo>
  installPlugin: (file: File) => Promise<PluginInstallResponse>
  installDiscoveredPlugin: (pluginId: string) => Promise<PluginInstallResponse>
  uninstallPlugin: (
    pluginId: string,
    dropTables?: boolean,
    removePermissions?: boolean,
  ) => Promise<void>
  enablePlugin: (pluginId: string) => Promise<void>
  disablePlugin: (pluginId: string) => Promise<void>
  updatePluginSettings: (
    pluginId: string,
    settings: Record<string, unknown>,
  ) => Promise<PluginSettingsResponse>

  // Computed getters
  getNavItems: () => PluginNavItem[]
  getRoutes: () => PluginRoute[]
  getEnabledPlugins: () => PluginSummary[]

  // Reset
  reset: () => void
}

export const usePlugins = create<PluginsState>((set, get) => ({
  plugins: [],
  discoveredPlugins: [],
  loadedPlugins: [],
  isLoading: false,
  isInitialized: false,
  error: null,

  fetchPlugins: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.get<PluginListResponse>('/plugins')
      set({ plugins: response.plugins, isLoading: false })
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to fetch plugins'
      set({ error, isLoading: false })
      throw e
    }
  },

  fetchDiscoveredPlugins: async () => {
    try {
      const response = await api.get<DiscoveredPluginsResponse>('/plugins/discovered')
      set({ discoveredPlugins: response.plugins })
    } catch (e) {
      console.error('Failed to fetch discovered plugins:', e)
    }
  },

  loadAllFrontends: async () => {
    const { plugins } = get()
    const enabledPlugins = plugins.filter((p) => p.is_enabled && p.has_frontend)

    const loaded: LoadedPlugin[] = []
    for (const plugin of enabledPlugins) {
      try {
        const loadedPlugin = await pluginLoader.loadPlugin(plugin)
        loaded.push(loadedPlugin)
      } catch (e) {
        console.error(`Failed to load frontend for plugin ${plugin.plugin_id}:`, e)
      }
    }

    set({ loadedPlugins: loaded, isInitialized: true })
  },

  getPluginInfo: async (pluginId: string) => {
    const response = await api.get<PluginInfo>(`/plugins/${pluginId}`)
    return response
  },

  installPlugin: async (file: File) => {
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/v1/plugins/install', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Install failed: ${response.status}`)
      }

      const result: PluginInstallResponse = await response.json()

      // Refresh plugin list and discovered plugins
      await get().fetchPlugins()
      await get().fetchDiscoveredPlugins()

      set({ isLoading: false })
      return result
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to install plugin'
      set({ error, isLoading: false })
      throw e
    }
  },

  installDiscoveredPlugin: async (pluginId: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.post<PluginInstallResponse>(
        `/plugins/discovered/${pluginId}/install`,
      )

      // Refresh plugin list and discovered plugins
      await get().fetchPlugins()
      await get().fetchDiscoveredPlugins()

      set({ isLoading: false })
      return response
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to install plugin'
      set({ error, isLoading: false })
      throw e
    }
  },

  uninstallPlugin: async (pluginId: string, dropTables = false, removePermissions = false) => {
    set({ isLoading: true, error: null })
    try {
      // Unload frontend if loaded
      await pluginLoader.unloadPlugin(pluginId)

      const params = new URLSearchParams()
      if (dropTables) {
        params.set('drop_tables', 'true')
      }
      if (removePermissions) {
        params.set('remove_permissions', 'true')
      }

      await api.delete<PluginUninstallResponse>(
        `/plugins/${pluginId}${params.toString() ? `?${params.toString()}` : ''}`,
      )

      // Refresh plugin list and loaded plugins
      await get().fetchPlugins()
      set({
        loadedPlugins: get().loadedPlugins.filter((p) => p.id !== pluginId),
        isLoading: false,
      })
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to uninstall plugin'
      set({ error, isLoading: false })
      throw e
    }
  },

  enablePlugin: async (pluginId: string) => {
    set({ isLoading: true, error: null })
    try {
      await api.post<PluginEnableResponse>(`/plugins/${pluginId}/enable`)

      // Refresh plugin list
      await get().fetchPlugins()

      // Load frontend if available
      const plugin = get().plugins.find((p) => p.plugin_id === pluginId)
      if (plugin?.has_frontend) {
        const loaded = await pluginLoader.loadPlugin(plugin)
        set((state) => ({
          loadedPlugins: [...state.loadedPlugins, loaded],
          isLoading: false,
        }))
      } else {
        set({ isLoading: false })
      }
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to enable plugin'
      set({ error, isLoading: false })
      throw e
    }
  },

  disablePlugin: async (pluginId: string) => {
    set({ isLoading: true, error: null })
    try {
      // Unload frontend first
      await pluginLoader.unloadPlugin(pluginId)

      await api.post<PluginEnableResponse>(`/plugins/${pluginId}/disable`)

      // Refresh and update state
      await get().fetchPlugins()
      set({
        loadedPlugins: get().loadedPlugins.filter((p) => p.id !== pluginId),
        isLoading: false,
      })
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to disable plugin'
      set({ error, isLoading: false })
      throw e
    }
  },

  updatePluginSettings: async (pluginId: string, settings: Record<string, unknown>) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.put<PluginSettingsResponse>(`/plugins/${pluginId}/settings`, {
        settings,
      })
      set({ isLoading: false })
      return response
    } catch (e) {
      const error = e instanceof Error ? e.message : 'Failed to update settings'
      set({ error, isLoading: false })
      throw e
    }
  },

  getNavItems: () => {
    const { loadedPlugins } = get()
    const items: PluginNavItem[] = []

    for (const plugin of loadedPlugins) {
      if (plugin.isLoaded && plugin.exports.getNavItems) {
        try {
          const pluginItems = plugin.exports.getNavItems()
          items.push(...pluginItems)
        } catch (e) {
          console.error(`Error getting nav items from plugin ${plugin.id}:`, e)
        }
      }
    }

    // Sort by order if provided
    return items.sort((a, b) => (a.order ?? 100) - (b.order ?? 100))
  },

  getRoutes: () => {
    const { loadedPlugins } = get()
    const routes: PluginRoute[] = []

    for (const plugin of loadedPlugins) {
      if (plugin.isLoaded && plugin.exports.getRoutes) {
        try {
          const pluginRoutes = plugin.exports.getRoutes()
          // Prefix routes with /plugins/{pluginId}
          const prefixedRoutes = pluginRoutes.map((route) => ({
            ...route,
            path: `/plugins/${plugin.id}${route.path}`,
          }))
          routes.push(...prefixedRoutes)
        } catch (e) {
          console.error(`Error getting routes from plugin ${plugin.id}:`, e)
        }
      }
    }

    return routes
  },

  getEnabledPlugins: () => {
    return get().plugins.filter((p) => p.is_enabled)
  },

  reset: () => {
    pluginLoader.unloadAll()
    set({
      plugins: [],
      discoveredPlugins: [],
      loadedPlugins: [],
      isLoading: false,
      isInitialized: false,
      error: null,
    })
  },
}))
