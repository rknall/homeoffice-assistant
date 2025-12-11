// frontend/src/pages/settings/UserRolesSettings.tsx

import { zodResolver } from '@hookform/resolvers/zod'
import { PlusCircle, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { api } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import { Label } from '@/components/ui/Label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/SelectRadix'
import { Separator } from '@/components/ui/Separator'
import type { Role, User, UserRole, UserRoleAssignment } from '@/types'

const assignRoleSchema = z.object({
  userId: z.string().min(1, 'User is required'),
  roleId: z.string().min(1, 'Role is required'),
  companyId: z.string().optional().nullable(),
})

type AssignRoleFormValues = z.infer<typeof assignRoleSchema>

export function UserRolesSettings() {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)

  const {
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<AssignRoleFormValues>({
    resolver: zodResolver(assignRoleSchema),
  })

  const selectedUserId = watch('userId')

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (selectedUserId) {
      fetchUserRoles(selectedUserId)
    } else {
      setUserRoles([])
    }
  }, [selectedUserId])

  const fetchData = async () => {
    try {
      const [usersData, rolesData] = await Promise.all([
        api.get<User[]>('/users'), // Assuming a /users endpoint exists
        api.get<Role[]>('/rbac/roles'),
      ])
      setUsers(usersData)
      setRoles(rolesData)
    } catch (error) {
      console.error('Failed to fetch initial data:', error)
      toast.error('Failed to load users or roles.')
    }
  }

  const fetchUserRoles = async (userId: string) => {
    try {
      const rolesData = await api.get<UserRole[]>(`/rbac/users/${userId}/roles`)
      setUserRoles(rolesData)
    } catch (error) {
      console.error('Failed to fetch user roles:', error)
      toast.error('Failed to load user roles.')
    }
  }

  const openModal = () => {
    reset({ userId: '', roleId: '', companyId: null })
    setIsModalOpen(true)
  }

  const onSubmit = async (values: AssignRoleFormValues) => {
    try {
      const assignment: UserRoleAssignment = {
        role_id: values.roleId,
        company_id: values.companyId || null,
      }
      await api.post(`/rbac/users/${values.userId}/roles`, assignment)
      toast.success('Role assigned successfully.')
      fetchUserRoles(values.userId)
      setIsModalOpen(false)
    } catch (error) {
      console.error('Failed to assign role:', error)
      toast.error('Failed to assign role.')
    }
  }

  const onRemoveRole = async (userRole: UserRole) => {
    if (!confirm('Are you sure you want to remove this role assignment?')) return
    try {
      const companyParam = userRole.company_id ? `?company_id=${userRole.company_id}` : ''
      await api.delete(`/rbac/users/${userRole.user_id}/roles/${userRole.role_id}${companyParam}`)
      toast.success('Role removed successfully.')
      fetchUserRoles(userRole.user_id)
    } catch (error) {
      console.error('Failed to remove role:', error)
      toast.error('Failed to remove role.')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">User Role Assignments</h2>
        <Button onClick={openModal}>
          <PlusCircle className="mr-2 h-4 w-4" /> Assign Role
        </Button>
      </div>

      <Separator />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="user-select">Select User</Label>
          <Select
            onValueChange={(value) => setValue('userId', value, { shouldValidate: true })}
            value={selectedUserId || ''}
          >
            <SelectTrigger id="user-select">
              <SelectValue placeholder="Select a user" />
            </SelectTrigger>
            <SelectContent>
              {users.map((user) => (
                <SelectItem key={user.id} value={user.id}>
                  {user.full_name || user.username}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.userId && <p className="text-sm text-red-500 mt-1">{errors.userId.message}</p>}
        </div>
      </div>

      {selectedUserId && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold">
            Roles for {users.find((u) => u.id === selectedUserId)?.username}
          </h3>
          {userRoles.length === 0 ? (
            <p className="text-gray-500">No roles assigned to this user.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {userRoles.map((userRole) => (
                <Card key={userRole.role.id + (userRole.company_id || '')}>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      {userRole.role.name}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onRemoveRole(userRole)}
                        aria-label={`Remove ${userRole.role.name}`}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </CardTitle>
                    <p className="text-sm text-gray-500">
                      {userRole.company_id
                        ? `Scoped to Company: ${userRole.company_id}`
                        : 'Global Scope'}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">{userRole.role.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Assign Role to User</DialogTitle>
            <DialogDescription>
              Select a user, a role, and optionally a company to assign a role.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="assign-user-select">User</Label>
              <Select
                onValueChange={(value) => setValue('userId', value, { shouldValidate: true })}
                value={watch('userId') || ''}
              >
                <SelectTrigger id="assign-user-select">
                  <SelectValue placeholder="Select a user" />
                </SelectTrigger>
                <SelectContent>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.full_name || user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.userId && (
                <p className="text-sm text-red-500 mt-1">{errors.userId.message}</p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="role-select">Role</Label>
              <Select
                onValueChange={(value) => setValue('roleId', value, { shouldValidate: true })}
                value={watch('roleId') || ''}
              >
                <SelectTrigger id="role-select">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={role.id}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.roleId && (
                <p className="text-sm text-red-500 mt-1">{errors.roleId.message}</p>
              )}
            </div>

            {/* TODO: Add Company Select */}
            {/* <div className="grid gap-2">
              <Label htmlFor="company-select">Company (Optional)</Label>
              <Select
                onValueChange={(value) => setValue('companyId', value, { shouldValidate: true })}
                value={watch('companyId') || ''}
              >
                <SelectTrigger id="company-select">
                  <SelectValue placeholder="Select a company (optional)" />
                </SelectTrigger>
                <SelectContent>
                  {companies.map((company) => (
                    <SelectItem key={company.id} value={company.id}>
                      {company.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div> */}

            <DialogFooter>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Assigning...' : 'Assign Role'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
