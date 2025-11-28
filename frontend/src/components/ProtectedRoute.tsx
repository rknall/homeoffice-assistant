import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/stores/auth'
import { PageSpinner } from '@/components/ui/Spinner'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, isLoading, isFirstRun } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <PageSpinner />
  }

  if (isFirstRun === true) {
    return <Navigate to="/setup" state={{ from: location }} replace />
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
