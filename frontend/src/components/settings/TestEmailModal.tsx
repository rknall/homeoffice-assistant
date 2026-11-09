// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'

interface TestEmailModalProps {
  isOpen: boolean
  address: string
  onAddressChange: (value: string) => void
  result: { success: boolean; message: string } | undefined
  isSending: boolean
  onSend: () => void
  onClose: () => void
}

export function TestEmailModal({
  isOpen,
  address,
  onAddressChange,
  result,
  isSending,
  onSend,
  onClose,
}: TestEmailModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Send Test Email">
      <div className="space-y-4">
        <Input
          label="Recipient Email"
          type="email"
          value={address}
          onChange={(e) => onAddressChange(e.target.value)}
          description="Enter the email address to receive the test email"
        />
        {result && <Alert variant={result.success ? 'success' : 'error'}>{result.message}</Alert>}
        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onSend} isLoading={isSending} disabled={!address}>
            Send Test Email
          </Button>
        </div>
      </div>
    </Modal>
  )
}
