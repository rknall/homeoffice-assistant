// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Card, CardContent } from '@/components/ui/Card'
import type { ExpenseReportPreview } from '@/types'

/** Total, item count and available-document cards from the report preview. */
export function EventSummaryCards({ preview }: { preview: ExpenseReportPreview | null }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm font-medium text-gray-500">Total Expenses</p>
          <p className="text-2xl font-bold text-gray-900">
            {preview?.total.toFixed(2)} {preview?.currency}
          </p>
          {preview?.conversion_rates && Object.keys(preview.conversion_rates).length > 0 && (
            <p className="text-xs text-gray-500 mt-1">
              {Object.entries(preview.conversion_rates)
                .map(([currency, rate]) => `1 ${currency} = ${rate.toFixed(4)} ${preview.currency}`)
                .join(', ')}
            </p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm font-medium text-gray-500">Number of Items</p>
          <p className="text-2xl font-bold text-gray-900">{preview?.expense_count || 0}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm font-medium text-gray-500">Documents Available</p>
          <p className="text-2xl font-bold text-gray-900">{preview?.documents_available || 0}</p>
        </CardContent>
      </Card>
    </div>
  )
}
