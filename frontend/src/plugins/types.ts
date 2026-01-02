// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { ComponentType } from 'react'

type IconComponent = ComponentType<{ className?: string }>
type LucideModule = typeof import('lucide-react')
type LucideIconName = keyof LucideModule['icons']

/**
 * Plugin capabilities from manifest
 */
export interface PluginCapabilities {
  backend: boolean
  frontend: boolean
  config: boolean
}

/**
 * A permission provided by a plugin
 */
export interface ProvidedPermission {
  code: string
  description: string
}

/**
 * Plugin manifest metadata
 */
export interface PluginManifest {
  id: string
  name: string
  version: string
  description: string
  author?: string
  homepage?: string
  license?: string
  minHostVersion?: string
  maxHostVersion?: string
  capabilities: PluginCapabilities
  /** @deprecated Use required_permissions instead */
  permissions: string[]
  /** Permissions the plugin requires from the host application */
  required_permissions?: string[]
  /** Permissions the plugin provides (adds to the system) */
  provided_permissions?: ProvidedPermission[]
  dependencies?: string[]
}

/**
 * Plugin summary for list views
 */
export interface PluginSummary {
  plugin_id: string
  plugin_version: string
  manifest: PluginManifest | null
  has_frontend: boolean
  has_backend: boolean
  created_at: string
  updated_at: string
}

/**
 * Full plugin info including settings
 */
export interface PluginInfo {
  plugin_id: string
  plugin_version: string
  manifest: PluginManifest | null
  config_schema: Record<string, unknown>
  settings: Record<string, unknown>
  migration_version: string | null
  has_frontend: boolean
  has_backend: boolean
  created_at: string
  updated_at: string
}

/**
 * Plugin list API response
 */
export interface PluginListResponse {
  plugins: PluginSummary[]
}

/**
 * Plugin install API response
 */
export interface PluginInstallResponse {
  success: boolean
  plugin_id: string
  plugin_name: string
  version: string
  message: string
}

/**
 * Plugin uninstall API response
 */
export interface PluginUninstallResponse {
  success: boolean
  plugin_id: string
  tables_dropped: boolean
  permissions_removed?: boolean
  message: string
}

/**
 * Plugin enable/disable API response
 */
export interface PluginEnableResponse {
  success: boolean
  plugin_id: string
  message: string
}

/**
 * Plugin settings API response
 */
export interface PluginSettingsResponse {
  success: boolean
  plugin_id: string
  settings: Record<string, unknown>
  message: string
}

/**
 * Navigation item provided by a plugin
 */
export interface PluginNavItem {
  id: string
  label: string
  icon?: IconComponent | LucideIconName
  path: string
  order?: number
}

/**
 * Route definition provided by a plugin
 */
export interface PluginRoute {
  path: string
  component: ComponentType
  exact?: boolean
}

/**
 * Widget components that plugins can provide
 */
export interface PluginWidgets {
  dashboard?: ComponentType
  eventDetail?: ComponentType<{ eventId: string }>
  companyDetail?: ComponentType<{ companyId: string }>
}

/**
 * Frontend exports from a plugin module
 */
export interface PluginExports {
  manifest: PluginManifest
  getNavItems?: () => PluginNavItem[]
  getRoutes?: () => PluginRoute[]
  widgets?: PluginWidgets
  onLoad?: () => Promise<void>
  onUnload?: () => Promise<void>
}

/**
 * Loaded plugin state
 */
export interface LoadedPlugin {
  id: string
  manifest: PluginManifest
  exports: PluginExports
  isLoaded: boolean
  loadError?: string
}

/**
 * Plugin loading state
 */
export type PluginLoadState = 'idle' | 'loading' | 'loaded' | 'error'

/**
 * A plugin discovered on disk but not yet installed
 */
export interface DiscoveredPlugin {
  plugin_id: string
  name: string
  version: string
  description: string
  author?: string
  has_frontend: boolean
  has_backend: boolean
}

/**
 * Discovered plugins API response
 */
export interface DiscoveredPluginsResponse {
  plugins: DiscoveredPlugin[]
}
