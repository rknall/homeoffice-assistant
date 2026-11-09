// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

interface RestoreConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
}

export function RestoreConfirmModal({ isOpen, onClose, onConfirm }: RestoreConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={() => onClose()} title="Confirm Restore">
      <div className="space-y-4">
        <p>Are you sure you want to restore from this backup? This will:</p>
        <ul className="list-disc list-inside text-sm text-gray-600">
          <li>Create a backup of current data</li>
          <li>Replace the database with the backup version</li>
          <li>Replace all avatar files</li>
          <li>Preserve your current admin account</li>
          <li>Run database migrations automatically</li>
          <li>Require an application restart</li>
        </ul>
        <div className="flex justify-end gap-3 pt-4">
          <Button variant="secondary" onClick={() => onClose()}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            Yes, Restore
          </Button>
        </div>
      </div>
    </Modal>
  )
}
