// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import type { UserRole, Uuid } from '@/types'

interface UserRolesCardProps {
  userRoles: UserRole[]
  getCompanyName: (companyId: Uuid | null | undefined) => string
  onAssignClick: () => void
  onRemove: (userRole: UserRole) => void
}

export function UserRolesCard({
  userRoles,
  getCompanyName,
  onAssignClick,
  onRemove,
}: UserRolesCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Role Assignments</CardTitle>
          <Button variant="secondary" onClick={() => onAssignClick()}>
            <Plus className="h-4 w-4 mr-2" />
            Assign Role
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {userRoles.length === 0 ? (
          <p className="text-gray-500 text-center py-4">
            No roles assigned to this user. Click "Assign Role" to add one.
          </p>
        ) : (
          <div className="divide-y divide-gray-200">
            {userRoles.map((userRole) => (
              <div
                key={`${userRole.role_id}-${userRole.company_id || 'global'}`}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <h4 className="font-medium text-gray-900">{userRole.role.name}</h4>
                  <p className="text-sm text-gray-500">
                    Scope: {getCompanyName(userRole.company_id)}
                  </p>
                  {userRole.role.description && (
                    <p className="text-sm text-gray-400">{userRole.role.description}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => onRemove(userRole)}
                  className="p-2 text-gray-400 hover:text-red-600"
                  title="Remove role"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
