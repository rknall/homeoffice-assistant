// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Save, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { Permission, RoleCreate, RoleUpdate, RoleWithPermissions, Uuid } from '@/types'

export function RoleDetail() {
  const { id } = useParams<{ id: Uuid }>()
  const isCreateMode = id === 'new'
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()

  const [role, setRole] = useState<RoleWithPermissions | null>(null)
  const [allPermissions, setAllPermissions] = useState<Permission[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set())
  const [hasChanges, setHasChanges] = useState(false)

  // Only Global Admin is fully immutable
  const isGlobalAdmin = role?.name === 'Global Admin'

  // Group permissions by module and sort
  const permissionsByModule = allPermissions.reduce(
    (acc, perm) => {
      if (!acc[perm.module]) {
        acc[perm.module] = []
      }
      acc[perm.module].push(perm)
      return acc
    },
    {} as Record<string, Permission[]>,
  )

  // Sort modules alphabetically
  const sortedModules = Object.keys(permissionsByModule).sort()

  // Sort permissions within each module
  for (const module of sortedModules) {
    permissionsByModule[module].sort((a, b) => a.code.localeCompare(b.code))
  }

  const fetchRole = useCallback(async () => {
    if (!id || isCreateMode) return
    try {
      const data = await api.get<RoleWithPermissions>(`/rbac/roles/${id}`)
      setRole(data)
      setName(data.name)
      setDescription(data.description || '')
      setSelectedPermissions(new Set(data.permissions.map((p) => p.code)))
    } catch {
      setError('Failed to load role')
    }
  }, [id, isCreateMode])

  const fetchPermissions = useCallback(async () => {
    try {
      const data = await api.get<Permission[]>('/rbac/permissions')
      setAllPermissions(data)
    } catch {
      setError('Failed to load permissions')
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await fetchPermissions()
      if (!isCreateMode) {
        await fetchRole()
      }
      setIsLoading(false)
    }
    loadData()
  }, [fetchRole, fetchPermissions, isCreateMode])

  useEffect(() => {
    setBreadcrumb([
      { label: 'Settings', href: '/settings' },
      { label: 'Roles', href: '/settings/roles' },
      { label: isCreateMode ? 'New Role' : role?.name || 'Loading...' },
    ])
  }, [role, setBreadcrumb, isCreateMode])

  const togglePermission = (code: string) => {
    if (isGlobalAdmin) return

    setSelectedPermissions((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(code)) {
        newSet.delete(code)
      } else {
        newSet.add(code)
      }
      return newSet
    })
    setHasChanges(true)
  }

  const handleNameChange = (value: string) => {
    setName(value)
    setHasChanges(true)
  }

  const handleDescriptionChange = (value: string) => {
    setDescription(value)
    setHasChanges(true)
  }

  const saveRole = async () => {
    if (!name.trim()) {
      toast.error('Role name is required')
      return
    }

    setIsSaving(true)
    try {
      if (isCreateMode) {
        const createData: RoleCreate = {
          name: name.trim(),
          description: description.trim() || undefined,
          permissions: Array.from(selectedPermissions),
        }
        const newRole = await api.post<RoleWithPermissions>('/rbac/roles', createData)
        toast.success('Role created successfully')
        navigate(`/settings/roles/${newRole.id}`, { replace: true })
      } else if (role) {
        const updateData: RoleUpdate = {
          name: name.trim(),
          description: description.trim() || undefined,
          permissions: Array.from(selectedPermissions),
        }
        await api.put(`/rbac/roles/${role.id}`, updateData)
        await fetchRole()
        toast.success('Role saved successfully')
        setHasChanges(false)
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to save role'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  const deleteRole = async () => {
    if (!role || !confirm('Are you sure you want to delete this role?')) {
      return
    }
    try {
      await api.delete(`/rbac/roles/${role.id}`)
      toast.success('Role deleted successfully')
      navigate('/settings/roles')
    } catch {
      toast.error('Failed to delete role')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!isCreateMode && !role) {
    return (
      <div className="p-6">
        <Alert variant="error">Role not found</Alert>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {isCreateMode ? 'New Role' : role?.name}
            </h1>
            {role?.is_system && <Badge variant="info">System Role</Badge>}
          </div>
          <div className="flex items-center gap-3">
            {!isGlobalAdmin && (
              <Button onClick={saveRole} disabled={isSaving || (!hasChanges && !isCreateMode)}>
                <Save className="h-4 w-4 mr-2" />
                {isSaving ? 'Saving...' : 'Save'}
              </Button>
            )}
            {!isCreateMode && !role?.is_system && (
              <button
                type="button"
                onClick={deleteRole}
                className="p-2 text-gray-400 hover:text-red-600"
                title="Delete role"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {isGlobalAdmin && (
        <Alert variant="info" className="mb-4">
          The Global Admin role cannot be modified. It always contains all permissions.
        </Alert>
      )}

      {/* Role Details Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Role Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              label="Role Name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              disabled={isGlobalAdmin}
              placeholder="Enter role name"
            />
            <div>
              <label htmlFor="role-description" className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                id="role-description"
                value={description}
                onChange={(e) => handleDescriptionChange(e.target.value)}
                disabled={isGlobalAdmin}
                rows={2}
                placeholder="Describe the purpose of this role..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Permissions Card */}
      <Card>
        <CardHeader>
          <CardTitle>Permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {sortedModules.map((module) => (
              <div key={module}>
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
                  {module.replace(/_/g, ' ')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {permissionsByModule[module].map((perm) => (
                    <div
                      key={perm.code}
                      className="flex items-start gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300"
                    >
                      <Checkbox
                        id={perm.code}
                        checked={selectedPermissions.has(perm.code)}
                        onCheckedChange={() => togglePermission(perm.code)}
                        disabled={isGlobalAdmin}
                      />
                      <label htmlFor={perm.code} className="flex-1 cursor-pointer">
                        <span className="block font-medium text-gray-900">{perm.code}</span>
                        {perm.description && (
                          <span className="block text-sm text-gray-500">{perm.description}</span>
                        )}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {selectedPermissions.size === 0 ? (
              <p className="text-gray-500">No permissions assigned to this role.</p>
            ) : (
              Array.from(selectedPermissions)
                .sort()
                .map((code) => (
                  <Badge key={code} variant="default">
                    {code}
                  </Badge>
                ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
