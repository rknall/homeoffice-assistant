// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight, FileText, Mail, Send } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import type { ExpenseSubmission, ExpenseSubmissionSummary } from '@/types'

interface SubmissionHistoryProps {
  eventId: string
}

const METHOD_ICONS: Record<string, React.ReactNode> = {
  download: <FileText className="h-4 w-4" />,
  email: <Mail className="h-4 w-4" />,
  portal: <Send className="h-4 w-4" />,
}

const METHOD_LABELS: Record<string, string> = {
  download: 'Downloaded',
  email: 'Emailed',
  portal: 'Portal',
}

export function SubmissionHistory({ eventId }: SubmissionHistoryProps) {
  const [submissions, setSubmissions] = useState<ExpenseSubmission[]>([])
  const [summary, setSummary] = useState<ExpenseSubmissionSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const fetchData = useCallback(async () => {
    try {
      const [submissionsData, summaryData] = await Promise.all([
        api.get<ExpenseSubmission[]>(`/events/${eventId}/submissions`),
        api.get<ExpenseSubmissionSummary>(`/events/${eventId}/submissions/summary`),
      ])
      setSubmissions(submissionsData)
      setSummary(summaryData)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load submission history')
    } finally {
      setIsLoading(false)
    }
  }, [eventId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    )
  }

  if (error) {
    return <div className="text-red-600 py-4">{error}</div>
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-gray-500">Total Submitted</p>
              <p className="text-xl font-bold text-gray-900">
                {summary.total_submitted.toFixed(2)} {summary.currency}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-gray-500">Awaiting Reimbursement</p>
              <p className="text-xl font-bold text-yellow-600">
                {summary.total_awaiting_reimbursement.toFixed(2)} {summary.currency}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-gray-500">Reimbursed</p>
              <p className="text-xl font-bold text-green-600">
                {summary.total_reimbursed.toFixed(2)} {summary.currency}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <p className="text-sm text-gray-500">Pending</p>
              <p className="text-xl font-bold text-gray-600">
                {summary.total_pending.toFixed(2)} {summary.currency}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Submission List */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Submission History</h3>
        </CardHeader>
        <CardContent>
          {submissions.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No submissions yet. Generate and download or email an expense report to create a
              submission.
            </p>
          ) : (
            <div className="space-y-3">
              {submissions.map((submission) => {
                const isExpanded = expandedIds.has(submission.id)
                return (
                  <div key={submission.id} className="border rounded-lg overflow-hidden">
                    <button
                      type="button"
                      onClick={() => toggleExpand(submission.id)}
                      className="w-full flex items-center gap-3 p-4 hover:bg-gray-50 text-left"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      )}

                      <div className="flex items-center gap-2 text-gray-600">
                        {METHOD_ICONS[submission.submission_method] || (
                          <FileText className="h-4 w-4" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">
                            {METHOD_LABELS[submission.submission_method] ||
                              submission.submission_method}
                          </span>
                          <span className="text-sm text-gray-500">
                            {submission.expense_count} expense
                            {submission.expense_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {formatDate(submission.submitted_at)}
                        </span>
                      </div>

                      <div className="text-right">
                        <span className="font-medium">
                          {Number(submission.total_amount).toFixed(2)} {submission.currency}
                        </span>
                      </div>
                    </button>

                    {isExpanded && submission.items && (
                      <div className="border-t bg-gray-50 px-4 py-3">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-gray-500 text-left">
                              <th className="pb-2">Description</th>
                              <th className="pb-2 text-right">Original</th>
                              <th className="pb-2 text-right">Converted</th>
                            </tr>
                          </thead>
                          <tbody className="text-gray-700">
                            {submission.items.map((item) => (
                              <tr key={item.id} className="border-t border-gray-200">
                                <td className="py-2">{item.description || 'No description'}</td>
                                <td className="py-2 text-right">
                                  {Number(item.amount).toFixed(2)} {item.currency}
                                </td>
                                <td className="py-2 text-right">
                                  {item.converted_amount
                                    ? `${Number(item.converted_amount).toFixed(2)} ${submission.currency}`
                                    : '-'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {submission.notes && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <p className="text-xs text-gray-500 uppercase font-medium">Notes</p>
                            <p className="text-sm text-gray-700">{submission.notes}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
