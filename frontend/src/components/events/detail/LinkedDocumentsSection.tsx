// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Eye, FileText, Link2Off, Pencil } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { useLocale } from '@/stores/locale'
import type { DocumentReference, DocumentType } from '@/types'
import { DOCUMENT_TYPE_COLORS, DOCUMENT_TYPE_LABELS } from '@/types'

interface LinkedDocumentsSectionProps {
  references: DocumentReference[]
  isLoading: boolean
  onPreview: (docId: number) => void
  onEdit: (reference: DocumentReference) => void
  onUnlink: (refId: string) => void
}

/** Table of documents linked to the event as references. */
export function LinkedDocumentsSection({
  references,
  isLoading,
  onPreview,
  onEdit,
  onUnlink,
}: LinkedDocumentsSectionProps) {
  const { formatDate } = useLocale()

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Linked Documents</h3>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : references.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No documents linked to this event yet. Link documents from Paperless below.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-500">Document</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Type</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Notes</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500">Linked</th>
                <th className="py-3 px-4 text-right font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {references.map((ref) => {
                const typeColors = ref.document_type
                  ? DOCUMENT_TYPE_COLORS[ref.document_type as DocumentType]
                  : null
                return (
                  <tr key={ref.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-red-500 shrink-0" />
                        <span className="font-medium">{ref.title}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {ref.document_type && typeColors ? (
                        <span
                          className={`px-2 py-1 rounded text-sm ${typeColors.bg} ${typeColors.text}`}
                        >
                          {DOCUMENT_TYPE_LABELS[ref.document_type as DocumentType]}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-600 text-sm">{ref.notes || '-'}</td>
                    <td className="py-3 px-4 text-gray-500 text-sm">
                      {formatDate(ref.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onPreview(ref.paperless_doc_id)}
                          className="p-2 text-gray-500 hover:text-gray-700"
                          title="View in Paperless"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onEdit(ref)}
                          className="p-2 text-gray-500 hover:text-gray-700"
                          title="Edit notes/type"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onUnlink(ref.id)}
                          className="p-2 text-red-500 hover:text-red-700"
                          title="Unlink from event"
                        >
                          <Link2Off className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
