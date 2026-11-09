// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight, Eye, FileText, Link2, Receipt, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Spinner } from '@/components/ui/Spinner'
import { useLocale } from '@/stores/locale'
import type { Document } from '@/types'

interface AvailableDocumentsSectionProps {
  documents: Document[]
  availableDocuments: Document[]
  isLoading: boolean
  isLinking: boolean
  onRefresh: () => void
  onPreview: (docId: number) => void
  onLink: (doc: Document) => void
  onCreateExpense: (doc: Document) => void
}

/** Collapsible list of Paperless documents not yet linked to the event. */
export function AvailableDocumentsSection({
  documents,
  availableDocuments,
  isLoading,
  isLinking,
  onRefresh,
  onPreview,
  onLink,
  onCreateExpense,
}: AvailableDocumentsSectionProps) {
  const { formatDate } = useLocale()
  const [isOpen, setIsOpen] = useState(true)

  return (
    <div>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full mb-4"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
          <h3 className="text-lg font-semibold text-gray-800">Available from Paperless</h3>
          <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded text-xs">
            {availableDocuments.length} unlinked
          </span>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            onRefresh()
          }}
          isLoading={isLoading}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </button>

      {isOpen && (
        <>
          <p className="text-sm text-gray-500 mb-4">
            Documents from Paperless matching this event. Documents already linked to expenses or as
            documents are hidden.
          </p>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : availableDocuments.length === 0 ? (
            <div className="mt-4 p-4 bg-green-50 rounded text-center text-green-700">
              {documents.length === 0
                ? "No documents found for this event. Documents are matched by the company's storage path and the event's custom field value in Paperless."
                : 'All documents have been linked.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Document</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Date</th>
                    <th className="py-3 px-4 text-right font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {availableDocuments.map((doc) => (
                    <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <FileText className="h-5 w-5 text-red-500 shrink-0" />
                          <span className="font-medium">{doc.title}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-500 text-sm">
                        {doc.created ? formatDate(doc.created) : '-'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => onPreview(doc.id)}
                            className="p-2 text-gray-500 hover:text-gray-700"
                            title="View in Paperless"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => onLink(doc)}
                            disabled={isLinking}
                            className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                            title="Link as document"
                          >
                            <span className="flex items-center gap-1">
                              <Link2 className="h-3 w-3" />
                              Document
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() => onCreateExpense(doc)}
                            className="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                            title="Create expense with this document"
                          >
                            <span className="flex items-center gap-1">
                              <Receipt className="h-3 w-3" />
                              Expense
                            </span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
