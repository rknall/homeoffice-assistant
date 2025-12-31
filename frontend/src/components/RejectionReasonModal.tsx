// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'

interface RejectionReasonModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (reason: string) => void
  expenseCount: number
  isLoading?: boolean
}

export function RejectionReasonModal({
  isOpen,
  onClose,
  onConfirm,
  expenseCount,
  isLoading = false,
}: RejectionReasonModalProps) {
  const [reason, setReason] = useState('')

  const handleConfirm = () => {
    if (reason.trim()) {
      onConfirm(reason.trim())
      setReason('')
    }
  }

  const handleClose = () => {
    setReason('')
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Mark as Rejected">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          You are about to mark {expenseCount} expense{expenseCount !== 1 ? 's' : ''} as rejected.
          Please provide a reason for the rejection.
        </p>

        <div>
          <label
            htmlFor="rejection-reason"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Rejection Reason
          </label>
          <textarea
            id="rejection-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter the reason for rejection..."
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            rows={3}
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button type="button" variant="secondary" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirm}
            disabled={!reason.trim() || isLoading}
            isLoading={isLoading}
          >
            Mark as Rejected
          </Button>
        </div>
      </div>
    </Modal>
  )
}
