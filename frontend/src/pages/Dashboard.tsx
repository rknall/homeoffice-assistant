// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { ActionItems, ExpenseBreakdown, StatsRow, UpcomingEvents } from '@/components/dashboard'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { DashboardSummary } from '@/types'

export function Dashboard() {
  const { clear: clearBreadcrumb } = useBreadcrumb()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    clearBreadcrumb()
  }, [clearBreadcrumb])

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const data = await api.get<DashboardSummary>('/dashboard/summary')
        setSummary(data)
      } catch {
        setError('Failed to load dashboard data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchDashboard()
  }, [])

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    )
  }

  if (error || !summary) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
        <Alert variant="error">{error || 'Failed to load dashboard'}</Alert>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats Row */}
      <StatsRow stats={summary.events_by_status} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upcoming Events */}
        <UpcomingEvents events={summary.upcoming_events} />

        {/* Action Items */}
        <ActionItems
          reportsNeeded={summary.events_needing_reports}
          incompleteTodos={summary.incomplete_todos}
        />
      </div>

      {/* Expense Breakdown */}
      <ExpenseBreakdown summary={summary.expense_summary} />
    </div>
  )
}
