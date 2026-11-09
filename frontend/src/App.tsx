// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { lazy, type ReactNode, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { Spinner } from '@/components/ui/Spinner'
import { Calendar } from '@/pages/Calendar'
import { Companies } from '@/pages/Companies'
import { CompanyDetail } from '@/pages/CompanyDetail'
import { Dashboard } from '@/pages/Dashboard'
import { Events } from '@/pages/Events'
import { Login } from '@/pages/Login'
import { Settings } from '@/pages/Settings'
import { Setup } from '@/pages/Setup'
import { PluginProvider, usePluginContext, usePluginRoutes } from '@/plugins'
import { useAuth } from '@/stores/auth'
import { useLocale } from '@/stores/locale'

const EventDetail = lazy(() =>
  import('@/pages/EventDetail').then((m) => ({ default: m.EventDetail })),
)
const BackupSettings = lazy(() =>
  import('@/pages/settings/BackupSettings').then((m) => ({ default: m.BackupSettings })),
)
const EmailTemplateSettings = lazy(() =>
  import('@/pages/settings/EmailTemplateSettings').then((m) => ({
    default: m.EmailTemplateSettings,
  })),
)
const HolidaySettings = lazy(() =>
  import('@/pages/settings/HolidaySettings').then((m) => ({ default: m.HolidaySettings })),
)
const IntegrationSettings = lazy(() =>
  import('@/pages/settings/IntegrationSettings').then((m) => ({
    default: m.IntegrationSettings,
  })),
)
const PluginSettings = lazy(() =>
  import('@/pages/settings/PluginSettings').then((m) => ({ default: m.PluginSettings })),
)
const RegionalSettings = lazy(() =>
  import('@/pages/settings/RegionalSettings').then((m) => ({ default: m.RegionalSettings })),
)
const RoleDetail = lazy(() =>
  import('@/pages/settings/RoleDetail').then((m) => ({ default: m.RoleDetail })),
)
const Roles = lazy(() => import('@/pages/settings/Roles').then((m) => ({ default: m.Roles })))
const TodoTemplateSettings = lazy(() =>
  import('@/pages/settings/TodoTemplateSettings').then((m) => ({
    default: m.TodoTemplateSettings,
  })),
)
const UserDetail = lazy(() =>
  import('@/pages/settings/UserDetail').then((m) => ({ default: m.UserDetail })),
)
const Users = lazy(() => import('@/pages/settings/Users').then((m) => ({ default: m.Users })))

function lazyPage(page: ReactNode) {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" />
        </div>
      }
    >
      {page}
    </Suspense>
  )
}

function AppRoutes() {
  const pluginRoutes = usePluginRoutes()
  const { isInitialized: pluginsInitialized } = usePluginContext()
  const location = useLocation()

  // If we're on a plugin route and plugins haven't initialized yet, show loading
  // This prevents the catch-all route from redirecting before plugins register their routes
  const isPluginRoute = location.pathname.startsWith('/plugins/')
  if (isPluginRoute && !pluginsInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/setup" element={<Setup />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:id" element={lazyPage(<EventDetail />)} />
        <Route path="/calendar" element={<Calendar />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/companies/:id" element={<CompanyDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/regional" element={lazyPage(<RegionalSettings />)} />
        <Route path="/settings/holidays" element={lazyPage(<HolidaySettings />)} />
        <Route path="/settings/integrations" element={lazyPage(<IntegrationSettings />)} />
        <Route path="/settings/plugins" element={lazyPage(<PluginSettings />)} />
        <Route path="/settings/templates" element={lazyPage(<EmailTemplateSettings />)} />
        <Route path="/settings/todo-templates" element={lazyPage(<TodoTemplateSettings />)} />
        <Route path="/settings/backup" element={lazyPage(<BackupSettings />)} />
        <Route path="/settings/roles" element={lazyPage(<Roles />)} />
        <Route path="/settings/roles/:id" element={lazyPage(<RoleDetail />)} />
        <Route path="/settings/users" element={lazyPage(<Users />)} />
        <Route path="/settings/users/:id" element={lazyPage(<UserDetail />)} />
        {/* Dynamic plugin routes */}
        {pluginRoutes}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export function App() {
  const { isLoading, user, checkSession, checkAuthStatus } = useAuth()
  const { fetchSettings: fetchLocaleSettings, isLoaded: localeLoaded } = useLocale()

  useEffect(() => {
    checkAuthStatus()
    checkSession()
  }, [checkAuthStatus, checkSession])

  // Fetch locale settings after user is authenticated
  useEffect(() => {
    if (user && !localeLoaded) {
      fetchLocaleSettings()
    }
  }, [user, localeLoaded, fetchLocaleSettings])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <PluginProvider>
      <AppRoutes />
    </PluginProvider>
  )
}
