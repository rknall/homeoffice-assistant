// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import type { Permission } from '@/types'

interface RolePermissionCardsProps {
  allPermissions: Permission[]
  selectedPermissions: Set<string>
  disabled: boolean
  onToggle: (code: string) => void
}

export function RolePermissionCards({
  allPermissions,
  selectedPermissions,
  disabled,
  onToggle,
}: RolePermissionCardsProps) {
  // Separate core permissions from plugin permissions
  const corePermissions = allPermissions.filter((p) => !p.plugin_id)
  const pluginPermissions = allPermissions.filter((p) => p.plugin_id)

  // Group core permissions by module
  const corePermissionsByModule = corePermissions.reduce(
    (acc, perm) => {
      if (!acc[perm.module]) {
        acc[perm.module] = []
      }
      acc[perm.module].push(perm)
      return acc
    },
    {} as Record<string, Permission[]>,
  )

  // Sort core modules alphabetically
  const sortedCoreModules = Object.keys(corePermissionsByModule).sort()

  // Sort permissions within each core module
  for (const module of sortedCoreModules) {
    corePermissionsByModule[module].sort((a, b) => a.code.localeCompare(b.code))
  }

  // Group plugin permissions by plugin_id
  const pluginPermissionsByPlugin = pluginPermissions.reduce(
    (acc, perm) => {
      const pluginId = perm.plugin_id || 'unknown'
      if (!acc[pluginId]) {
        acc[pluginId] = []
      }
      acc[pluginId].push(perm)
      return acc
    },
    {} as Record<string, Permission[]>,
  )

  // Sort plugin IDs alphabetically
  const sortedPluginIds = Object.keys(pluginPermissionsByPlugin).sort()

  // Sort permissions within each plugin
  for (const pluginId of sortedPluginIds) {
    pluginPermissionsByPlugin[pluginId].sort((a, b) => a.code.localeCompare(b.code))
  }
  return (
    <>
      {/* Core Permissions Card */}
      <Card>
        <CardHeader>
          <CardTitle>Core Permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {sortedCoreModules.map((module) => (
              <div key={module}>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                  {module.replace(/_/g, ' ')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {corePermissionsByModule[module].map((perm) => (
                    <div
                      key={perm.code}
                      className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300"
                    >
                      <Checkbox
                        id={perm.code}
                        checked={selectedPermissions.has(perm.code)}
                        onCheckedChange={() => onToggle(perm.code)}
                        disabled={disabled}
                      />
                      <label htmlFor={perm.code} className="flex-1 cursor-pointer">
                        <span className="block font-medium text-gray-900">{perm.code}</span>
                        {perm.description && (
                          <span className="block text-sm text-gray-500">{perm.description}</span>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Plugin Permissions Card - Only show if there are plugin permissions */}
      {sortedPluginIds.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Plugin Permissions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-4">
              These permissions are provided by installed plugins and can be assigned to roles.
            </p>
            <div className="space-y-6">
              {sortedPluginIds.map((pluginId) => (
                <div key={pluginId}>
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                      {pluginId}
                    </h3>
                    <Badge variant="info" className="text-xs">
                      Plugin
                    </Badge>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {pluginPermissionsByPlugin[pluginId].map((perm) => (
                      <div
                        key={perm.code}
                        className="flex items-start gap-3 p-3 rounded-lg border border-blue-100 bg-blue-50/30 hover:border-blue-200"
                      >
                        <Checkbox
                          id={perm.code}
                          checked={selectedPermissions.has(perm.code)}
                          onCheckedChange={() => onToggle(perm.code)}
                          disabled={disabled}
                        />
                        <label htmlFor={perm.code} className="flex-1 cursor-pointer">
                          <span className="block font-medium text-gray-900">{perm.code}</span>
                          {perm.description && (
                            <span className="block text-sm text-gray-500">{perm.description}</span>
                          )}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  )
}
