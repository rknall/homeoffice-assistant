// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Save, User as UserIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api, errorMessage } from '@/api/client'
import { AssignRoleModal } from '@/components/settings/AssignRoleModal'
import { EffectivePermissionsCard } from '@/components/settings/EffectivePermissionsCard'
import { UserDetailsCard } from '@/components/settings/UserDetailsCard'
import { UserProfileCard } from '@/components/settings/UserProfileCard'
import { UserRolesCard } from '@/components/settings/UserRolesCard'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useCompanies } from '@/stores/companies'
import { confirmAction } from '@/stores/confirm'
import type { Role, User, UserRole, Uuid } from '@/types'

export function UserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()

  const isNewUser = id === 'new'

  const [user, setUser] = useState<User | null>(null)
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [allRoles, setAllRoles] = useState<Role[]>([])
  const companies = useCompanies((s) => s.companies)
  const fetchCompanies = useCompanies((s) => s.fetchCompanies)
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
    } catch (e) {
      setError(errorMessage(e, 'Failed to load user'))
    }
  }, [id, isNewUser])

  const fetchUserRoles = useCallback(async () => {
    if (!id || isNewUser) return
    try {
      const data = await api.get<UserRole[]>(`/rbac/users/${id}/roles`)
      setUserRoles(data)
    } catch (e) {
      setError(errorMessage(e, 'Failed to load user roles'))
    }
  }, [id, isNewUser])

  const fetchAllRoles = useCallback(async () => {
    try {
      const data = await api.get<Role[]>('/rbac/roles')
      setAllRoles(data)
    } catch (e) {
      setError(errorMessage(e, 'Failed to load roles'))
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
      const message = errorMessage(e, 'Failed to save user')
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

      const updatedUser = await api.upload<User>(`/users/${user.id}/avatar`, formData)
      setUser(updatedUser)
      setUseGravatar(false)
      toast.success('Avatar uploaded successfully')
    } catch (e) {
      const message = errorMessage(e, 'Failed to upload avatar')
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
      const message = errorMessage(e, 'Failed to remove avatar')
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
      const message = errorMessage(e, 'Failed to assign role')
      toast.error(message)
      throw e
    }
  }

  const removeRole = async (userRole: UserRole) => {
    if (
      !user ||
      !(await confirmAction({
        title: 'Remove role assignment',
        message: 'Are you sure you want to remove this role assignment?',
        confirmLabel: 'Remove',
      }))
    ) {
      return
    }
    try {
      const companyParam = userRole.company_id ? `?company_id=${userRole.company_id}` : ''
      await api.delete(`/rbac/users/${user.id}/roles/${userRole.role_id}${companyParam}`)
      await fetchUserRoles()
      toast.success('Role removed successfully')
    } catch (e) {
      toast.error(errorMessage(e, 'Failed to remove role'))
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

      {!isNewUser && user && (
        <UserProfileCard
          user={user}
          useGravatar={useGravatar}
          isUploading={isUploading}
          fileInputRef={fileInputRef}
          onFileSelect={handleFileSelect}
          onDeleteAvatar={handleDeleteAvatar}
          onUseGravatarChange={handleUseGravatarChange}
        />
      )}

      <UserDetailsCard
        isNewUser={isNewUser}
        fullName={fullName}
        username={username}
        email={email}
        password={password}
        isActive={isActive}
        onFullNameChange={handleFullNameChange}
        onUsernameChange={handleUsernameChange}
        onEmailChange={handleEmailChange}
        onPasswordChange={handlePasswordChange}
        onIsActiveChange={handleIsActiveChange}
      />

      {!isNewUser && user && (
        <UserRolesCard
          userRoles={userRoles}
          getCompanyName={getCompanyName}
          onAssignClick={() => setIsAssignModalOpen(true)}
          onRemove={removeRole}
        />
      )}

      {!isNewUser && user && (
        <EffectivePermissionsCard user={user} getCompanyName={getCompanyName} />
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
