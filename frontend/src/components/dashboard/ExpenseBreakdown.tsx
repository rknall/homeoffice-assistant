// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import type { ExpenseSummary } from '@/types'

interface ExpenseBreakdownProps {
  summary: ExpenseSummary
}

const CATEGORY_COLORS: Record<string, { bg: string; bar: string }> = {
  travel: { bg: 'bg-blue-500', bar: 'bg-blue-100' },
  accommodation: { bg: 'bg-emerald-500', bar: 'bg-emerald-100' },
  meals: { bg: 'bg-amber-500', bar: 'bg-amber-100' },
  transport: { bg: 'bg-purple-500', bar: 'bg-purple-100' },
  equipment: { bg: 'bg-rose-500', bar: 'bg-rose-100' },
  communication: { bg: 'bg-cyan-500', bar: 'bg-cyan-100' },
  other: { bg: 'bg-gray-400', bar: 'bg-gray-100' },
}

const CATEGORY_LABELS: Record<string, string> = {
  travel: 'Travel',
  accommodation: 'Accommodation',
  meals: 'Meals',
  transport: 'Transport',
  equipment: 'Equipment',
  communication: 'Communication',
  other: 'Other',
}

export function ExpenseBreakdown({ summary }: ExpenseBreakdownProps) {
  const hasExpenses = summary.total > 0

  if (!hasExpenses) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Expenses <span className="text-sm font-normal text-gray-500">(Last 90 days)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 text-center py-4">No expenses recorded</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            Expenses <span className="text-sm font-normal text-gray-500">(Last 90 days)</span>
          </CardTitle>
          <span className="text-lg font-semibold text-gray-900">
            {summary.base_currency} {summary.total.toFixed(2)}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {/* Stacked bar chart */}
        <div className="h-6 rounded-full overflow-hidden flex bg-gray-100 mb-4">
          {summary.by_category.map((cat) => {
            const colors = CATEGORY_COLORS[cat.category] || CATEGORY_COLORS.other
            return (
              <div
                key={cat.category}
                className={`${colors.bg} transition-all duration-300`}
                style={{ width: `${cat.percentage}%` }}
                title={`${CATEGORY_LABELS[cat.category] || cat.category}: ${cat.percentage.toFixed(1)}%`}
              />
            )
          })}
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {summary.by_category.map((cat) => {
            const colors = CATEGORY_COLORS[cat.category] || CATEGORY_COLORS.other
            const label = CATEGORY_LABELS[cat.category] || cat.category
            return (
              <div key={cat.category} className="flex items-center gap-2 text-sm">
                <div className={`w-3 h-3 rounded-full ${colors.bg}`} />
                <span className="text-gray-600 truncate">{label}</span>
                <span className="text-gray-400 ml-auto">{cat.percentage.toFixed(0)}%</span>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
