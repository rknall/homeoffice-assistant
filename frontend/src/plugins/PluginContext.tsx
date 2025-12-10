// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { createContext, type ReactNode, useContext, useEffect, useState } from 'react'
import { usePlugins } from './registry'

interface PluginContextValue {
  isInitialized: boolean
  isLoading: boolean
  error: string | null
}

const PluginContext = createContext<PluginContextValue | null>(null)

interface PluginProviderProps {
  children: ReactNode
}

/**
 * Provider component that initializes the plugin system.
 * Fetches installed plugins on mount and loads enabled frontend modules.
 */
export function PluginProvider({ children }: PluginProviderProps) {
  const [initError, setInitError] = useState<string | null>(null)
  const { fetchPlugins, loadAllFrontends, isInitialized, isLoading, error } = usePlugins()

  useEffect(() => {
    async function initPlugins() {
      try {
        // Fetch list of installed plugins
        await fetchPlugins()
        // Load frontend modules for enabled plugins
        await loadAllFrontends()
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : 'Failed to initialize plugins'
        setInitError(errorMsg)
        console.error('Plugin initialization error:', e)
      }
    }

    initPlugins()
  }, [fetchPlugins, loadAllFrontends])

  const value: PluginContextValue = {
    isInitialized,
    isLoading,
    error: initError || error,
  }

  return <PluginContext.Provider value={value}>{children}</PluginContext.Provider>
}

/**
 * Hook to access plugin context.
 * Must be used within a PluginProvider.
 */
export function usePluginContext(): PluginContextValue {
  const context = useContext(PluginContext)
  if (!context) {
    throw new Error('usePluginContext must be used within a PluginProvider')
  }
  return context
}
