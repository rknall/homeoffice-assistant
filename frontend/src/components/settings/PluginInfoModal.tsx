// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import type { PluginInfo } from '@/plugins/types'

interface PluginInfoModalProps {
  isOpen: boolean
  isLoading: boolean
  pluginInfo: PluginInfo | null
  onClose: () => void
}

export function PluginInfoModal({ isOpen, isLoading, pluginInfo, onClose }: PluginInfoModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Plugin Configuration" size="lg">
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : pluginInfo ? (
        <div className="space-y-6">
          {/* Plugin Info */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">Information</h3>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-500">ID</dt>
                <dd className="font-mono">{pluginInfo.plugin_id}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Version</dt>
                <dd>{pluginInfo.plugin_version}</dd>
              </div>
              {pluginInfo.migration_version && (
                <div>
                  <dt className="text-gray-500">Migration Version</dt>
                  <dd className="font-mono text-xs">{pluginInfo.migration_version}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Required Permissions */}
          {((pluginInfo.manifest?.required_permissions &&
            pluginInfo.manifest.required_permissions.length > 0) ||
            (pluginInfo.manifest?.permissions &&
              pluginInfo.manifest.permissions.length > 0 &&
              !pluginInfo.manifest?.required_permissions)) && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Required Permissions</h3>
              <p className="text-xs text-gray-500 mb-2">
                Permissions this plugin needs from the host application
              </p>
              <div className="flex flex-wrap gap-2">
                {(pluginInfo.manifest.required_permissions || pluginInfo.manifest.permissions).map(
                  (perm) => (
                    <Badge key={perm} variant="default" className="font-mono text-xs">
                      {perm}
                    </Badge>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Provided Permissions */}
          {pluginInfo.manifest?.provided_permissions &&
            pluginInfo.manifest.provided_permissions.length > 0 && (
              <div>
                <h3 className="font-medium text-gray-900 mb-2">Provided Permissions</h3>
                <p className="text-xs text-gray-500 mb-2">
                  Custom permissions this plugin adds to the system
                </p>
                <div className="space-y-2">
                  {pluginInfo.manifest.provided_permissions.map((perm) => (
                    <div key={perm.code} className="flex items-start gap-2 bg-gray-50 p-2 rounded">
                      <Badge variant="info" className="font-mono text-xs shrink-0">
                        {perm.code}
                      </Badge>
                      {perm.description && (
                        <span className="text-xs text-gray-600">{perm.description}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Settings */}
          {Object.keys(pluginInfo.settings || {}).length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Settings</h3>
              <Alert variant="info">
                Plugin settings configuration will be available in a future update.
              </Alert>
            </div>
          )}

          {/* Config Schema Info */}
          {Object.keys(pluginInfo.config_schema || {}).length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Configuration Schema</h3>
              <pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-48">
                {JSON.stringify(pluginInfo.config_schema, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-gray-500">No configuration available for this plugin.</p>
      )}
    </Modal>
  )
}
