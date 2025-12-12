// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus, Save, Trash2, User as UserIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { Company, Role, User, UserRole, Uuid } from '@/types'
import { getGravatarUrl } from '@/utils/gravatar'

interface AssignRoleModalProps {
  isOpen: boolean
  onClose: () => void
  onAssign: (roleId: Uuid, companyId: Uuid | null) => Promise<void>
  roles: Role[]
  companies: Company[]
  existingRoles: UserRole[]
}

function AssignRoleModal({
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

export function UserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()

  const isNewUser = id === 'new'

  const [user, setUser] = useState<User | null>(null)
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [allRoles, setAllRoles] = useState<Role[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(!isNewUser)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)

  // Form state for user details
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [fullName, setFullName] = useState('')
  const [useGravatar, setUseGravatar] = useState(true)
  const [hasChanges, setHasChanges] = useState(isNewUser)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchUser = useCallback(async () => {
    if (!id || isNewUser) return
    try {
      const data = await api.get<User>(`/users/${id}`)
      setUser(data)
      setUsername(data.username)
      setEmail(data.email)
      setIsActive(data.is_active)
      setFullName(data.full_name || '')
      setUseGravatar(data.use_gravatar)
    } catch {
      setError('Failed to load user')
    }
  }, [id, isNewUser])

  const fetchUserRoles = useCallback(async () => {
    if (!id || isNewUser) return
    try {
      const data = await api.get<UserRole[]>(`/rbac/users/${id}/roles`)
      setUserRoles(data)
    } catch {
      setError('Failed to load user roles')
    }
  }, [id, isNewUser])

  const fetchAllRoles = useCallback(async () => {
    try {
      const data = await api.get<Role[]>('/rbac/roles')
      setAllRoles(data)
    } catch {
      setError('Failed to load roles')
    }
  }, [])

  const fetchCompanies = useCallback(async () => {
    try {
      const data = await api.get<Company[]>('/companies')
      setCompanies(data)
    } catch {
      // Companies might not be critical, don't show error
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      if (isNewUser) {
        await Promise.all([fetchAllRoles(), fetchCompanies()])
      } else {
        setIsLoading(true)
        await Promise.all([fetchUser(), fetchUserRoles(), fetchAllRoles(), fetchCompanies()])
        setIsLoading(false)
      }
    }
    loadData()
  }, [fetchUser, fetchUserRoles, fetchAllRoles, fetchCompanies, isNewUser])

  useEffect(() => {
    if (isNewUser) {
      setBreadcrumb([
        { label: 'Settings', href: '/settings' },
        { label: 'Users', href: '/settings/users' },
        { label: 'New User' },
      ])
    } else if (user) {
      setBreadcrumb([
        { label: 'Settings', href: '/settings' },
        { label: 'Users', href: '/settings/users' },
        { label: user.full_name || user.username },
      ])
    }
  }, [user, setBreadcrumb, isNewUser])

  const handleUsernameChange = (value: string) => {
    setUsername(value)
    setHasChanges(true)
  }

  const handleEmailChange = (value: string) => {
    setEmail(value)
    setHasChanges(true)
  }

  const handlePasswordChange = (value: string) => {
    setPassword(value)
    setHasChanges(true)
  }

  const handleIsActiveChange = (checked: boolean) => {
    setIsActive(checked)
    setHasChanges(true)
  }

  const handleFullNameChange = (value: string) => {
    setFullName(value)
    setHasChanges(true)
  }

  const handleUseGravatarChange = (checked: boolean) => {
    setUseGravatar(checked)
    setHasChanges(true)
  }

  const saveUser = async () => {
    if (!username.trim() || !email.trim()) {
      toast.error('Username and email are required')
      return
    }

    if (isNewUser && !password.trim()) {
      toast.error('Password is required for new users')
      return
    }

    if (isNewUser && password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    setIsSaving(true)
    try {
      if (isNewUser) {
        const newUser = await api.post<User>('/users', {
          username: username.trim(),
          email: email.trim(),
          password: password,
        })
        toast.success('User created successfully')
        navigate(`/settings/users/${newUser.id}`)
      } else if (user) {
        await api.put(`/users/${user.id}`, {
          username: username.trim(),
          email: email.trim(),
          is_active: isActive,
          full_name: fullName.trim() || null,
          use_gravatar: useGravatar,
          ...(password.trim() && { password: password.trim() }),
        })
        await fetchUser()
        toast.success('User saved successfully')
        setHasChanges(false)
        setPassword('')
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to save user'
      toast.error(message)
    } finally {
      setIsSaving(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !user) return

    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`/api/v1/users/${user.id}/avatar`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to upload avatar')
      }

      const updatedUser: User = await response.json()
      setUser(updatedUser)
      setUseGravatar(false)
      toast.success('Avatar uploaded successfully')
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to upload avatar'
      toast.error(message)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDeleteAvatar = async () => {
    if (!user) return

    setIsUploading(true)

    try {
      const updatedUser = await api.delete<User>(`/users/${user.id}/avatar`)
      setUser(updatedUser)
      setUseGravatar(true)
      toast.success('Avatar removed successfully')
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to remove avatar'
      toast.error(message)
    } finally {
      setIsUploading(false)
    }
  }

  const assignRole = async (roleId: Uuid, companyId: Uuid | null) => {
    if (!user) return
    try {
      await api.post(`/rbac/users/${user.id}/roles`, {
        role_id: roleId,
        company_id: companyId,
      })
      await fetchUserRoles()
      toast.success('Role assigned successfully')
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to assign role'
      toast.error(message)
      throw e
    }
  }

  const removeRole = async (userRole: UserRole) => {
    if (!user || !confirm('Are you sure you want to remove this role assignment?')) {
      return
    }
    try {
      const companyParam = userRole.company_id ? `?company_id=${userRole.company_id}` : ''
      await api.delete(`/rbac/users/${user.id}/roles/${userRole.role_id}${companyParam}`)
      await fetchUserRoles()
      toast.success('Role removed successfully')
    } catch {
      toast.error('Failed to remove role')
    }
  }

  const getCompanyName = (companyId: Uuid | null | undefined) => {
    if (!companyId) return 'Global'
    const company = companies.find((c) => c.id === companyId)
    return company?.name || companyId
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!isNewUser && !user) {
    return (
      <div className="p-6">
        <Alert variant="error">User not found</Alert>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-16 h-16 rounded-lg bg-gray-100">
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.full_name || user.username}
                  className="w-16 h-16 rounded-lg object-cover"
                />
              ) : (
                <UserIcon className="h-8 w-8 text-gray-600" />
              )}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {isNewUser ? 'New User' : user?.full_name || user?.username}
              </h1>
              {!isNewUser && user && <p className="text-gray-500">{user.email}</p>}
            </div>
            {!isNewUser && user && !user.is_active && <Badge variant="warning">Inactive</Badge>}
          </div>
          <Button onClick={saveUser} disabled={isSaving || !hasChanges}>
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : isNewUser ? 'Create User' : 'Save'}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Profile Card - only show for existing users */}
      {!isNewUser && user && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <img
                  src={
                    useGravatar
                      ? getGravatarUrl(user.email, 128)
                      : user.avatar_url || getGravatarUrl(user.email, 128)
                  }
                  alt={user.full_name || user.username}
                  className="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
                />
              </div>
              <div className="flex-1 space-y-3">
                <p className="text-sm font-medium text-gray-700">Profile Picture</p>
                <div className="flex flex-wrap gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    isLoading={isUploading}
                  >
                    Upload Image
                  </Button>
                  {user.avatar_url && !user.use_gravatar && (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={handleDeleteAvatar}
                      isLoading={isUploading}
                    >
                      Remove
                    </Button>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <Checkbox
                    id="use-gravatar"
                    checked={useGravatar}
                    onCheckedChange={handleUseGravatarChange}
                  />
                  <label htmlFor="use-gravatar" className="text-sm text-gray-600">
                    Use Gravatar
                  </label>
                </div>
                <p className="text-xs text-gray-500">
                  Gravatar uses the email address to show a profile picture.{' '}
                  <a
                    href="https://gravatar.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Learn more
                  </a>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* User Details Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>User Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => handleFullNameChange(e.target.value)}
              placeholder="Enter full name"
            />
            <Input
              label="Username"
              value={username}
              onChange={(e) => handleUsernameChange(e.target.value)}
              placeholder="Enter username"
            />
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => handleEmailChange(e.target.value)}
              placeholder="Enter email"
            />
            <Input
              label={isNewUser ? 'Password' : 'New Password (leave blank to keep current)'}
              type="password"
              value={password}
              onChange={(e) => handlePasswordChange(e.target.value)}
              placeholder={isNewUser ? 'Enter password' : 'Enter new password'}
            />
            {!isNewUser && (
              <div className="flex items-center gap-3">
                <Checkbox
                  id="is-active"
                  checked={isActive}
                  onCheckedChange={handleIsActiveChange}
                />
                <label htmlFor="is-active" className="text-sm font-medium text-gray-700">
                  Account is active
                </label>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Role Assignments Card - only show for existing users */}
      {!isNewUser && user && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Role Assignments</CardTitle>
              <Button variant="secondary" onClick={() => setIsAssignModalOpen(true)}>
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
                      onClick={() => removeRole(userRole)}
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
      )}

      {/* Effective Permissions Card - only show for existing users */}
      {!isNewUser && user && (
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
      )}

      {/* Assign Role Modal */}
      {!isNewUser && user && (
        <AssignRoleModal
          isOpen={isAssignModalOpen}
          onClose={() => setIsAssignModalOpen(false)}
          onAssign={assignRole}
          roles={allRoles}
          companies={companies}
          existingRoles={userRoles}
        />
      )}
    </div>
  )
}
