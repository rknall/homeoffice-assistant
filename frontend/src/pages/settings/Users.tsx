// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronRight, Plus, User as UserIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/stores/auth'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { User } from '@/types'

export function Users() {
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchUsers = useCallback(async () => {
    try {
      const data = await api.get<User[]>('/users')
      setUsers(data)
    } catch {
      setError('Failed to load users')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Users' }])
  }, [setBreadcrumb])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const getRoleCount = (user: User) => {
    // Count global permissions as one "global" role scope
    // and each company as a separate scope
    const scopes = new Set<string>()
    if (user.permissions.length > 0) {
      scopes.add('global')
    }
    Object.keys(user.company_permissions).forEach((companyId) => {
      if (user.company_permissions[companyId].length > 0) {
        scopes.add(companyId)
      }
    })
    return scopes.size
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <Button onClick={() => navigate('/settings/users/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : users.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No users found.</p>
          ) : (
            <div className="divide-y divide-gray-200">
              {users.map((user) => (
                <button
                  type="button"
                  key={user.id}
                  className="flex items-center justify-between py-4 cursor-pointer hover:bg-gray-50 -mx-4 px-4 rounded w-full text-left"
                  onClick={() => navigate(`/settings/users/${user.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100">
                      {user.avatar_url ? (
                        <img
                          src={user.avatar_url}
                          alt={user.full_name || user.username}
                          className="w-10 h-10 rounded-lg object-cover"
                        />
                      ) : (
                        <UserIcon className="h-5 w-5 text-gray-600" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">
                        {user.full_name || user.username}
                      </h3>
                      <p className="text-sm text-gray-500">{user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {currentUser?.id === user.id && <Badge variant="info">You</Badge>}
                    {!user.is_active && <Badge variant="warning">Inactive</Badge>}
                    <span className="text-sm text-gray-500">
                      {getRoleCount(user)} role scope{getRoleCount(user) !== 1 ? 's' : ''}
                    </span>
                    <ChevronRight className="h-4 w-4 text-gray-400" />
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
