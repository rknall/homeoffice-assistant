// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Route } from 'react-router-dom'
import { usePlugins } from './registry'

/**
 * Component that renders dynamic routes from loaded plugins.
 * Use this inside a Routes component to add plugin pages.
 */
export function PluginRoutes() {
  const routes = usePlugins((state) => state.getRoutes())

  return (
    <>
      {routes.map((route) => (
        <Route key={route.path} path={route.path} element={<route.component />} />
      ))}
    </>
  )
}
