// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useMemo } from 'react'
import { Route } from 'react-router-dom'
import { usePlugins } from './registry'
import type { PluginRoute } from './types'

/**
 * Hook that returns Route elements for loaded plugins.
 * Use the returned array directly inside a Routes component.
 *
 * @example
 * ```tsx
 * <Routes>
 *   <Route path="/" element={<Home />} />
 *   {usePluginRoutes()}
 * </Routes>
 * ```
 */
export function usePluginRoutes() {
  // Select the loadedPlugins array directly to avoid infinite re-renders
  const loadedPlugins = usePlugins((state) => state.loadedPlugins)

  // Memoize routes derivation to prevent unnecessary recalculations
  const routes = useMemo(() => {
    const result: PluginRoute[] = []

    for (const plugin of loadedPlugins) {
      if (plugin.isLoaded && plugin.exports.getRoutes) {
        try {
          const pluginRoutes = plugin.exports.getRoutes()
          const prefixedRoutes = pluginRoutes.map((route) => ({
            ...route,
            path: `/plugins/${plugin.id}${route.path}`,
          }))
          result.push(...prefixedRoutes)
        } catch (e) {
          console.error(`Error getting routes from plugin ${plugin.id}:`, e)
        }
      }
    }

    return result
  }, [loadedPlugins])

  return routes.map((route) => (
    <Route key={route.path} path={route.path} element={<route.component />} />
  ))
}
