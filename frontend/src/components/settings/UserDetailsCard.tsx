// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import { Input } from '@/components/ui/Input'

interface UserDetailsCardProps {
  isNewUser: boolean
  fullName: string
  username: string
  email: string
  password: string
  isActive: boolean
  onFullNameChange: (value: string) => void
  onUsernameChange: (value: string) => void
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onIsActiveChange: (checked: boolean) => void
}

export function UserDetailsCard({
  isNewUser,
  fullName,
  username,
  email,
  password,
  isActive,
  onFullNameChange,
  onUsernameChange,
  onEmailChange,
  onPasswordChange,
  onIsActiveChange,
}: UserDetailsCardProps) {
  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>User Details</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Input
            label="Full Name"
            value={fullName}
            onChange={(e) => onFullNameChange(e.target.value)}
            placeholder="Enter full name"
          />
          <Input
            label="Username"
            value={username}
            onChange={(e) => onUsernameChange(e.target.value)}
            placeholder="Enter username"
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
            placeholder="Enter email"
          />
          <Input
            label={isNewUser ? 'Password' : 'New Password (leave blank to keep current)'}
            type="password"
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            placeholder={isNewUser ? 'Enter password' : 'Enter new password'}
          />
          {!isNewUser && (
            <div className="flex items-center gap-3">
              <Checkbox id="is-active" checked={isActive} onCheckedChange={onIsActiveChange} />
              <label htmlFor="is-active" className="text-sm font-medium text-gray-700">
                Account is active
              </label>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
