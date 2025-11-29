// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useState } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '@/stores/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Alert } from '@/components/ui/Alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Footer } from '@/components/layout/Footer'
import logoImage from '@/assets/logo.png'

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, error, clearError, isFirstRun } = useAuth()
  const [isLoading, setIsLoading] = useState(false)

  const from = location.state?.from?.pathname || '/'

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    clearError()
    try {
      await login(data.username, data.password)
      navigate(from, { replace: true })
    } catch {
      // Error is handled by the store
    } finally {
      setIsLoading(false)
    }
  }

  if (isFirstRun) {
    return (
      <div className="min-h-screen flex flex-col bg-gray-100">
        <div className="flex-1 flex items-center justify-center px-4">
          <Card className="w-full max-w-md">
            <CardHeader className="text-center">
              <img
                src={logoImage}
                alt="Travel Manager"
                className="h-20 w-20 mx-auto mb-4 object-contain"
              />
              <CardTitle>Welcome to Travel Manager</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                No users have been created yet. Create the first admin account to get started.
              </p>
              <Link to="/setup">
                <Button className="w-full">Create Admin Account</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <div className="flex-1 flex items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <img
              src={logoImage}
              alt="Travel Manager"
              className="h-20 w-20 mx-auto mb-4 object-contain"
              style={{ objectPosition: 'left bottom' }}
            />
            <CardTitle>Sign in to Travel Manager</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {error && (
                <Alert variant="error">{error}</Alert>
              )}
              <Input
                label="Username"
                {...register('username')}
                error={errors.username?.message}
                autoComplete="username"
              />
              <Input
                label="Password"
                type="password"
                {...register('password')}
                error={errors.password?.message}
                autoComplete="current-password"
              />
              <Button type="submit" className="w-full" isLoading={isLoading}>
                Sign in
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
      <Footer />
    </div>
  )
}
