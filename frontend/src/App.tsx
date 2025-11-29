import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/stores/auth'
import { useLocale } from '@/stores/locale'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { Login } from '@/pages/Login'
import { Setup } from '@/pages/Setup'
import { Dashboard } from '@/pages/Dashboard'
import { Companies } from '@/pages/Companies'
import { CompanyDetail } from '@/pages/CompanyDetail'
import { Events } from '@/pages/Events'
import { EventDetail } from '@/pages/EventDetail'
import { Settings } from '@/pages/Settings'
import { Spinner } from '@/components/ui/Spinner'

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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
