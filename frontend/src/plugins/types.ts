// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { ComponentType } from 'react'

/**
 * Plugin capabilities from manifest
 */
export interface PluginCapabilities {
  backend: boolean
  frontend: boolean
  config: boolean
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
  permissions: string[]
  dependencies?: string[]
}

/**
 * Plugin summary for list views
 */
export interface PluginSummary {
  plugin_id: string
  plugin_version: string
  is_enabled: boolean
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
  is_enabled: boolean
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
  message: string
}

/**
 * Plugin enable/disable API response
 */
export interface PluginEnableResponse {
  success: boolean
  plugin_id: string
  is_enabled: boolean
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
  icon?: ComponentType<{ className?: string }>
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
