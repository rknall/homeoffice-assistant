// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { RefObject } from 'react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Checkbox } from '@/components/ui/Checkbox'
import type { User } from '@/types'
import { getGravatarUrl } from '@/utils/gravatar'

interface UserProfileCardProps {
  user: User
  useGravatar: boolean
  isUploading: boolean
  fileInputRef: RefObject<HTMLInputElement | null>
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onDeleteAvatar: () => void
  onUseGravatarChange: (checked: boolean) => void
}

export function UserProfileCard({
  user,
  useGravatar,
  isUploading,
  fileInputRef,
  onFileSelect,
  onDeleteAvatar,
  onUseGravatarChange,
}: UserProfileCardProps) {
  return (
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
                onChange={onFileSelect}
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
                  onClick={onDeleteAvatar}
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
                onCheckedChange={onUseGravatarChange}
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
                Learn more about Gravatar
              </a>
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
