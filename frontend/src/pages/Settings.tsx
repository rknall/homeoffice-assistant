// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useBreadcrumb } from '@/stores/breadcrumb'

export function Settings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings' }])
  }, [setBreadcrumb])

  // Redirect to the first settings sub-page
  return <Navigate to="/settings/regional" replace />
}
