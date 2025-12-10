// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

export { PluginLoader, pluginLoader } from './loader'
export { PluginProvider, usePluginContext } from './PluginContext'
export { PluginRoutes } from './PluginRoutes'
export { usePlugins } from './registry'
export type {
  LoadedPlugin,
  PluginCapabilities,
  PluginEnableResponse,
  PluginExports,
  PluginInfo,
  PluginInstallResponse,
  PluginListResponse,
  PluginLoadState,
  PluginManifest,
  PluginNavItem,
  PluginRoute,
  PluginSettingsResponse,
  PluginSummary,
  PluginUninstallResponse,
  PluginWidgets,
} from './types'
