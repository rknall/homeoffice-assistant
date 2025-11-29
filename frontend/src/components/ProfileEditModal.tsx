// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '@/api/client'
import type { User, AuthResponse } from '@/types'
import { getGravatarUrl } from '@/utils/gravatar'
import { Modal } from '@/components/ui/Modal'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Alert'

const profileSchema = z.object({
  full_name: z.string().max(200).optional(),
  use_gravatar: z.boolean(),
  current_password: z.string().optional(),
  new_password: z.string().min(8, 'Password must be at least 8 characters').optional().or(z.literal('')),
  confirm_password: z.string().optional(),
}).refine(
  (data) => {
    if (data.new_password && data.new_password !== data.confirm_password) {
      return false
    }
    return true
  },
  {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  }
).refine(
  (data) => {
    if (data.new_password && !data.current_password) {
      return false
    }
    return true
  },
  {
    message: 'Current password is required to change password',
    path: ['current_password'],
  }
)

type ProfileForm = z.infer<typeof profileSchema>

interface ProfileEditModalProps {
  isOpen: boolean
  onClose: () => void
  user: User
  onUpdate: (user: User) => void
}

export function ProfileEditModal({ isOpen, onClose, user, onUpdate }: ProfileEditModalProps) {
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user.full_name || '',
      use_gravatar: user.use_gravatar,
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const useGravatar = watch('use_gravatar')

  const onSubmit = async (data: ProfileForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const payload: Record<string, unknown> = {
        full_name: data.full_name || null,
        use_gravatar: data.use_gravatar,
      }

      if (data.new_password) {
        payload.current_password = data.current_password
        payload.new_password = data.new_password
      }

      const result = await api.put<AuthResponse>('/auth/me', payload)
      onUpdate(result.user)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update profile')
    } finally {
      setIsSaving(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/v1/auth/me/avatar', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to upload avatar')
      }

      const result: AuthResponse = await response.json()
      onUpdate(result.user)
      setValue('use_gravatar', false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upload avatar')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDeleteAvatar = async () => {
    setIsUploading(true)
    setError(null)

    try {
      const result = await api.delete<AuthResponse>('/auth/me/avatar')
      onUpdate(result.user)
      setValue('use_gravatar', true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete avatar')
    } finally {
      setIsUploading(false)
    }
  }

  const currentAvatarUrl = useGravatar
    ? getGravatarUrl(user.email, 128)
    : (user.avatar_url || getGravatarUrl(user.email, 128))

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Profile" size="lg">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && <Alert variant="error">{error}</Alert>}

        {/* Avatar Section */}
        <div className="flex items-start gap-6">
          <div className="flex-shrink-0">
            <img
              src={currentAvatarUrl}
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
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                {...register('use_gravatar')}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600">Use Gravatar</span>
            </label>
            <p className="text-xs text-gray-500">
              Gravatar uses your email address to show a profile picture.{' '}
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

        {/* Basic Info */}
        <div className="space-y-4">
          <Input
            label="Full Name"
            {...register('full_name')}
            error={errors.full_name?.message}
          />
          <Input
            label="Email"
            value={user.email}
            disabled
            description="Email cannot be changed"
          />
          <Input
            label="Username"
            value={user.username}
            disabled
            description="Username cannot be changed"
          />
        </div>

        {/* Password Change */}
        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-sm font-medium text-gray-900 mb-4">Change Password</h3>
          <div className="space-y-4">
            <Input
              label="Current Password"
              type="password"
              {...register('current_password')}
              error={errors.current_password?.message}
            />
            <Input
              label="New Password"
              type="password"
              {...register('new_password')}
              error={errors.new_password?.message}
            />
            <Input
              label="Confirm New Password"
              type="password"
              {...register('confirm_password')}
              error={errors.confirm_password?.message}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  )
}
