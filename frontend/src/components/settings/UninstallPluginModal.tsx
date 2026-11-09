// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { PluginSummary } from '@/plugins/types'

/**
 * Build a warning message for destructive uninstall options.
 */
function buildUninstallWarning(
  dropTables: boolean,
  removePermissions: boolean,
  deleteFiles: boolean,
): string {
  const actions: string[] = []
  if (dropTables) actions.push('permanently delete all data stored by this plugin')
  if (removePermissions) actions.push('remove its custom permissions from roles')
  if (deleteFiles) actions.push('delete plugin files from disk')

  if (actions.length === 0) return ''
  if (actions.length === 1) return `This will ${actions[0]}.`
  const last = actions.pop()
  return `This will ${actions.join(', ')} and ${last}.`
}

interface UninstallPluginModalProps {
  isOpen: boolean
  plugin: PluginSummary | null
  isProcessing: boolean
  dropTables: boolean
  removePermissions: boolean
  deleteFiles: boolean
  onDropTablesChange: (value: boolean) => void
  onRemovePermissionsChange: (value: boolean) => void
  onDeleteFilesChange: (value: boolean) => void
  onConfirm: () => void
  onClose: () => void
}

export function UninstallPluginModal({
  isOpen,
  plugin: selectedPlugin,
  isProcessing,
  dropTables,
  removePermissions,
  deleteFiles,
  onDropTablesChange,
  onRemovePermissionsChange,
  onDeleteFilesChange,
  onConfirm,
  onClose,
}: UninstallPluginModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Uninstall Plugin">
      <div className="space-y-4">
        <p className="text-gray-600">
          Are you sure you want to uninstall{' '}
          <strong>{selectedPlugin?.manifest?.name || selectedPlugin?.plugin_id}</strong>?
        </p>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={dropTables}
            onChange={(e) => onDropTablesChange(e.target.checked)}
            className="rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">
            Also delete plugin database tables (data will be lost)
          </span>
        </label>

        {/* Only show remove permissions if plugin has provided permissions */}
        {selectedPlugin?.manifest?.provided_permissions &&
          selectedPlugin.manifest.provided_permissions.length > 0 && (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={removePermissions}
                onChange={(e) => onRemovePermissionsChange(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">
                Also remove plugin-provided permissions from the system
              </span>
            </label>
          )}

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={deleteFiles}
            onChange={(e) => onDeleteFilesChange(e.target.checked)}
            className="rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">
            Also delete plugin files from disk (cannot be reinstalled without re-uploading)
          </span>
        </label>

        {(dropTables || removePermissions || deleteFiles) && (
          <Alert variant="warning">
            {buildUninstallWarning(dropTables, removePermissions, deleteFiles)}
          </Alert>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} isLoading={isProcessing}>
            Uninstall
          </Button>
        </div>
      </div>
    </Modal>
  )
}
