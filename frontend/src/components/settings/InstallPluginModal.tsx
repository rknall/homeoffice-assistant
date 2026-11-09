// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'

interface InstallPluginModalProps {
  isOpen: boolean
  isInstalling: boolean
  upgradeMode: boolean
  onUpgradeModeChange: (value: boolean) => void
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
  onClose: () => void
}

export function InstallPluginModal({
  isOpen,
  isInstalling,
  upgradeMode,
  onUpgradeModeChange,
  onFileUpload,
  onClose,
}: InstallPluginModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Install Plugin">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Upload a plugin package (ZIP file) to install a new plugin or to upgrade an existing one.
        </p>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <Upload className="h-10 w-10 text-gray-400 mx-auto mb-4" />
          <label
            htmlFor="plugin-upload"
            className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
          >
            Choose a file
            <input
              id="plugin-upload"
              type="file"
              accept=".zip"
              onChange={onFileUpload}
              className="hidden"
              disabled={isInstalling}
            />
          </label>
          <p className="text-sm text-gray-500 mt-2">or drag and drop</p>
        </div>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={upgradeMode}
            onChange={(e) => onUpgradeModeChange(e.target.checked)}
            className="rounded border-gray-300"
            disabled={isInstalling}
          />
          <span className="text-sm text-gray-700">
            Upgrade existing plugin (replace with new version)
          </span>
        </label>
        {isInstalling && (
          <div className="flex items-center justify-center gap-2">
            <Spinner className="h-5 w-5" />
            <span className="text-sm text-gray-600">
              {upgradeMode ? 'Upgrading plugin...' : 'Installing plugin...'}
            </span>
          </div>
        )}
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose} disabled={isInstalling}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  )
}
