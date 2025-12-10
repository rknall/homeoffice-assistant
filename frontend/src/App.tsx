// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { Spinner } from '@/components/ui/Spinner'
import { Companies } from '@/pages/Companies'
import { CompanyDetail } from '@/pages/CompanyDetail'
import { Dashboard } from '@/pages/Dashboard'
import { EventDetail } from '@/pages/EventDetail'
import { Events } from '@/pages/Events'
import { Login } from '@/pages/Login'
import { Settings } from '@/pages/Settings'
import { Setup } from '@/pages/Setup'
import { BackupSettings } from '@/pages/settings/BackupSettings'
import { EmailTemplateSettings } from '@/pages/settings/EmailTemplateSettings'
import { IntegrationSettings } from '@/pages/settings/IntegrationSettings'
import { PluginSettings } from '@/pages/settings/PluginSettings'
import { RegionalSettings } from '@/pages/settings/RegionalSettings'
import { PluginProvider, usePluginRoutes } from '@/plugins'
import { useAuth } from '@/stores/auth'
import { useLocale } from '@/stores/locale'

function AppRoutes() {
  const pluginRoutes = usePluginRoutes()

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
        <Route path="/events/:id" element={<EventDetail />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/companies/:id" element={<CompanyDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/regional" element={<RegionalSettings />} />
        <Route path="/settings/integrations" element={<IntegrationSettings />} />
        <Route path="/settings/plugins" element={<PluginSettings />} />
        <Route path="/settings/templates" element={<EmailTemplateSettings />} />
        <Route path="/settings/backup" element={<BackupSettings />} />
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
