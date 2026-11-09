// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/Button'
import { Checkbox } from '@/components/ui/Checkbox'
import { Modal } from '@/components/ui/Modal'
import type { Company, Role, UserRole, Uuid } from '@/types'

interface AssignRoleModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (roleId: Uuid, companyId: Uuid | null) => Promise<void>
  roles: Role[]
  companies: Company[]
  existingRoles: UserRole[]
}

export function AssignRoleModal({
  isOpen,
  onClose,
  onAssign,
  roles,
  companies,
  existingRoles,
}: AssignRoleModalProps) {
  const [selectedRoleId, setSelectedRoleId] = useState<Uuid | null>(null)
  const [selectedCompanyId, setSelectedCompanyId] = useState<Uuid | null>(null)
  const [isGlobalScope, setIsGlobalScope] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!selectedRoleId) {
      toast.error('Please select a role')
      return
    }

    // Check if this exact assignment already exists
    const exists = existingRoles.some(
      (ur) =>
        ur.role_id === selectedRoleId &&
        (isGlobalScope ? ur.company_id === null : ur.company_id === selectedCompanyId),
    )
    if (exists) {
      toast.error('This role assignment already exists')
      return
    }

    setIsSubmitting(true)
    try {
      await onAssign(selectedRoleId, isGlobalScope ? null : selectedCompanyId)
      onClose()
      setSelectedRoleId(null)
      setSelectedCompanyId(null)
      setIsGlobalScope(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Assign Role" size="md">
      <div className="space-y-4">
        <div>
          <label htmlFor="role-select" className="block text-sm font-medium text-gray-700 mb-1">
            Role
          </label>
          <select
            id="role-select"
            value={selectedRoleId || ''}
            onChange={(e) => setSelectedRoleId(e.target.value || null)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a role...</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          <Checkbox
            id="global-scope"
            checked={isGlobalScope}
            onCheckedChange={(checked: boolean) => setIsGlobalScope(checked)}
          />
          <label htmlFor="global-scope" className="text-sm font-medium text-gray-700">
            Global scope (applies to all companies)
          </label>
        </div>

        {!isGlobalScope && (
          <div>
            <label
              htmlFor="company-select"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Company
            </label>
            <select
              id="company-select"
              value={selectedCompanyId || ''}
              onChange={(e) => setSelectedCompanyId(e.target.value || null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a company...</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting || !selectedRoleId}>
            {isSubmitting ? 'Assigning...' : 'Assign Role'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
