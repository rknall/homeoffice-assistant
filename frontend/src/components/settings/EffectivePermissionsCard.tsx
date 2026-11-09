// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import type { User, Uuid } from '@/types'

interface EffectivePermissionsCardProps {
  user: User
  getCompanyName: (companyId: Uuid | null | undefined) => string
}

export function EffectivePermissionsCard({ user, getCompanyName }: EffectivePermissionsCardProps) {
  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Effective Permissions</CardTitle>
      </CardHeader>
      <CardContent>
        {user.permissions.length === 0 && Object.keys(user.company_permissions).length === 0 ? (
          <p className="text-gray-500">No permissions. Assign roles to grant permissions.</p>
        ) : (
          <div className="space-y-4">
            {user.permissions.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Global Permissions</h4>
                <div className="flex flex-wrap gap-2">
                  {user.permissions.sort().map((perm) => (
                    <Badge key={perm} variant="default">
                      {perm}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {Object.entries(user.company_permissions).map(([companyId, perms]) => (
              <div key={companyId}>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                  {getCompanyName(companyId)} Permissions
                </h4>
                <div className="flex flex-wrap gap-2">
                  {perms.sort().map((perm) => (
                    <Badge key={perm} variant="info">
                      {perm}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
