// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Time Tracking Plugin Frontend Module
 *
 * This file exports the plugin manifest and provides the frontend integration
 * including navigation items, routes, and widgets for injection into host pages.
 */

import type { PluginExports, PluginManifest, PluginNavItem, PluginRoute } from '@/plugins/types'
import { TimeTrackingPage, CompanyTimeSettingsWidget } from './components'

// Plugin manifest matching the backend plugin.manifest.json
const manifest: PluginManifest = {
  id: 'time-tracking',
  name: 'Time Tracking',
  version: '0.1.0',
  description: 'Track working hours with Austrian labor law compliance, vacation balances, and comp time',
  author: 'Roland Knall',
  license: 'GPL-2.0-only',
  capabilities: {
    backend: true,
    frontend: true,
    config: true,
  },
  permissions: [],
  required_permissions: [
    'events.read',
    'companies.read',
  ],
  provided_permissions: [
    { code: 'time-tracking.records.read', description: 'View time records' },
    { code: 'time-tracking.records.write', description: 'Create and edit time records' },
    { code: 'time-tracking.records.delete', description: 'Delete time records' },
    { code: 'time-tracking.reports.read', description: 'View time reports' },
    { code: 'time-tracking.reports.submit', description: 'Submit timesheets' },
    { code: 'time-tracking.settings.write', description: 'Configure time tracking settings' },
  ],
}

// Navigation items for the plugin
function getNavItems(): PluginNavItem[] {
  return [
    {
      id: 'time-tracking',
      label: 'Time Tracking',
      icon: 'Clock',
      path: '/plugins/time-tracking',
      order: 25,
    },
  ]
}

// Route definitions for the plugin
function getRoutes(): PluginRoute[] {
  return [
    {
      path: '',
      component: TimeTrackingPageWrapper,
      exact: true,
    },
  ]
}

// Wrapper component to handle company selection
function TimeTrackingPageWrapper() {
  // This would typically get the selected company from context/props
  // For now, we'll need to integrate with the host app's company selection
  return (
    <div className="p-6">
      <p className="text-gray-500">
        Select a company to view time tracking records.
      </p>
    </div>
  )
}

// Export the plugin
const exports: PluginExports = {
  manifest,
  getNavItems,
  getRoutes,
  widgets: {
    companyDetail: CompanyTimeSettingsWidget,
  },
}

export default exports
export { manifest, getNavItems, getRoutes }
export * from './types'
export * from './api'
export * from './components'
