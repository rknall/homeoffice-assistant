// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/stores/auth'

const setupSchema = z
  .object({
    fullName: z
      .string()
      .min(1, 'Display name is required')
      .max(200, 'Display name must be at most 200 characters'),
    username: z
      .string()
      .min(3, 'Username must be at least 3 characters')
      .max(50, 'Username must be at most 50 characters')
      .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
    email: z.string().min(1, 'Email is required').email('Please enter a valid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[a-zA-Z]/, 'Password must contain at least one letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type SetupForm = z.infer<typeof setupSchema>

interface PasswordValidation {
  minLength: boolean
  hasLetter: boolean
  hasNumber: boolean
  hasSpecial: boolean
}

function PasswordRequirements({
  password,
  confirmPassword,
}: {
  password: string
  confirmPassword: string
}) {
  const validation: PasswordValidation = {
    minLength: password.length >= 8,
    hasLetter: /[a-zA-Z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\;'/`~]/.test(password),
  }

  const passwordsMatch =
    password.length > 0 && confirmPassword.length > 0 && password === confirmPassword
  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword

  const RequirementItem = ({
    met,
    label,
    recommended,
  }: {
    met: boolean
    label: string
    recommended?: boolean
  }) => (
    <div
      className={`flex items-center gap-2 text-sm ${met ? 'text-green-600' : recommended ? 'text-gray-500' : 'text-gray-500'}`}
    >
      <span
        className={`w-4 h-4 flex items-center justify-center rounded-full text-xs ${
          met ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
        }`}
      >
        {met ? '✓' : '○'}
      </span>
      <span>
        {label}
        {recommended && !met ? ' (recommended)' : ''}
      </span>
    </div>
  )

  return (
    <div className="mt-2 space-y-1">
      <RequirementItem met={validation.minLength} label="At least 8 characters" />
      <RequirementItem met={validation.hasLetter} label="Contains a letter" />
      <RequirementItem met={validation.hasNumber} label="Contains a number" />
      <RequirementItem
        met={validation.hasSpecial}
        label="Contains a special character"
        recommended
      />
      {(passwordsMatch || passwordsMismatch) && (
        <div
          className={`flex items-center gap-2 text-sm ${passwordsMatch ? 'text-green-600' : 'text-red-600'}`}
        >
          <span
            className={`w-4 h-4 flex items-center justify-center rounded-full text-xs ${
              passwordsMatch ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
            }`}
          >
            {passwordsMatch ? '✓' : '✗'}
          </span>
          <span>{passwordsMatch ? 'Passwords match' : 'Passwords do not match'}</span>
        </div>
      )}
    </div>
  )
}

export function Setup() {
  const navigate = useNavigate()
  const { register: registerUser, error, clearError, isFirstRun } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [usernameManuallyEdited, setUsernameManuallyEdited] = useState(false)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SetupForm>({
    resolver: zodResolver(setupSchema),
  })

  const fullName = watch('fullName')
  const username = watch('username')

  const generateUsername = useCallback((name: string): string => {
    if (!name) return ''
    const firstName = name.trim().split(/\s+/)[0].toLowerCase()
    return firstName.replace(/[^a-z0-9_]/g, '')
  }, [])

  const checkUsernameAvailability = useCallback(
    async (usernameToCheck: string): Promise<boolean> => {
      if (!usernameToCheck || usernameToCheck.length < 3) return true
      try {
        const response = await api.get<{ available: boolean }>(
          `/auth/check-username/${usernameToCheck}`,
        )
        return response.available
      } catch {
        return true
      }
    },
    [],
  )

  useEffect(() => {
    if (usernameManuallyEdited || !fullName) return

    const updateUsername = async () => {
      let baseUsername = generateUsername(fullName)
      if (!baseUsername) return

      const isAvailable = await checkUsernameAvailability(baseUsername)
      if (!isAvailable) {
        const randomSuffix = Math.floor(Math.random() * 90) + 10
        baseUsername = `${baseUsername}${randomSuffix}`
      }
      setValue('username', baseUsername)
    }

    const timeoutId = setTimeout(updateUsername, 300)
    return () => clearTimeout(timeoutId)
  }, [fullName, usernameManuallyEdited, generateUsername, checkUsernameAvailability, setValue])

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUsernameManuallyEdited(true)
    register('username').onChange(e)
  }

  const onSubmit = async (data: SetupForm) => {
    setIsLoading(true)
    clearError()
    try {
      await registerUser(data.username, data.email, data.password, data.fullName)
      navigate('/', { replace: true })
    } catch {
      // Error is handled by the store
    } finally {
      setIsLoading(false)
    }
  }

  if (isFirstRun === false) {
    navigate('/login', { replace: true })
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create Admin Account</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 mb-4">
            Set up your administrator account to start using HomeOffice Assistant.
          </p>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}
            <Input
              label="Full Name"
              {...register('fullName')}
              error={errors.fullName?.message}
              autoComplete="name"
              placeholder="Your full name"
            />
            <Input
              label="Username"
              {...register('username')}
              onChange={handleUsernameChange}
              value={username || ''}
              error={errors.username?.message}
              autoComplete="username"
            />
            <Input
              label="Email"
              type="email"
              {...register('email')}
              error={errors.email?.message}
              autoComplete="email"
            />
            <div>
              <Input
                label="Password"
                type="password"
                {...register('password', {
                  onChange: (e) => setPassword(e.target.value),
                })}
                error={errors.password?.message}
                autoComplete="new-password"
              />
              <PasswordRequirements password={password} confirmPassword={confirmPassword} />
            </div>
            <Input
              label="Confirm Password"
              type="password"
              {...register('confirmPassword', {
                onChange: (e) => setConfirmPassword(e.target.value),
              })}
              error={errors.confirmPassword?.message}
              autoComplete="new-password"
            />
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Create Account
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
