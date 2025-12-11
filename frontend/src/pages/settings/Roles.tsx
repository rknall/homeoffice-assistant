// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronRight, Plus, Shield, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { Role, RoleWithPermissions } from '@/types'

export function Roles() {
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [roles, setRoles] = useState<RoleWithPermissions[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRoles = useCallback(async () => {
    try {
      const rolesData = await api.get<Role[]>('/rbac/roles')
      // Fetch full role details with permissions for each role
      const rolesWithPermissions = await Promise.all(
        rolesData.map((role) => api.get<RoleWithPermissions>(`/rbac/roles/${role.id}`)),
      )
      setRoles(rolesWithPermissions)
    } catch {
      setError('Failed to load roles')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Roles' }])
  }, [setBreadcrumb])

  useEffect(() => {
    fetchRoles()
  }, [fetchRoles])

  const deleteRole = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this role?')) return
    try {
      await api.delete(`/rbac/roles/${id}`)
      toast.success('Role deleted successfully')
      await fetchRoles()
    } catch {
      toast.error('Failed to delete role')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Roles</h1>
        <Button onClick={() => navigate('/settings/roles/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Create Role
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Roles</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : roles.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No roles configured. Create your first role to get started.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {roles.map((role) => (
                <button
                  type="button"
                  key={role.id}
                  className="flex items-center justify-between py-4 cursor-pointer hover:bg-gray-50 -mx-4 px-4 rounded w-full text-left"
                  onClick={() => navigate(`/settings/roles/${role.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-100">
                      <Shield className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{role.name}</h3>
                      <p className="text-sm text-gray-500">
                        {role.permissions.length} permission
                        {role.permissions.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {role.is_system && <Badge variant="info">System</Badge>}
                    <div className="flex items-center gap-2">
                      {!role.is_system && (
                        <button
                          type="button"
                          onClick={(e) => deleteRole(e, role.id)}
                          className="p-1 text-gray-400 hover:text-red-600"
                          title="Delete role"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
