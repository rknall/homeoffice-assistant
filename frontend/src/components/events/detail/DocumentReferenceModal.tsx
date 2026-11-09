// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from 'react'
import { api, errorMessage } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { DocumentReference, DocumentReferenceUpdate, DocumentType } from '@/types'

interface DocumentReferenceModalProps {
  reference: DocumentReference | null
  onClose: () => void
  eventId: string
  onSaved: () => Promise<void>
  onError: (message: string | null) => void
}

/** Modal that edits the notes, type and report flag of a linked document. */
export function DocumentReferenceModal({
  reference,
  onClose,
  eventId,
  onSaved,
  onError,
}: DocumentReferenceModalProps) {
  const [notes, setNotes] = useState('')
  const [type, setType] = useState<DocumentType | ''>('')
  const [includeInReport, setIncludeInReport] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setNotes(reference?.notes || '')
    setType((reference?.document_type as DocumentType) || '')
    setIncludeInReport(reference?.include_in_report ?? false)
  }, [reference])

  const save = async () => {
    if (!reference) return
    setIsSaving(true)
    try {
      const data: DocumentReferenceUpdate = {
        notes: notes || null,
        document_type: (type as DocumentType) || null,
        include_in_report: includeInReport,
      }
      await api.put(`/events/${eventId}/document-references/${reference.id}`, data)
      await onSaved()
      onClose()
    } catch (e) {
      onError(errorMessage(e, 'Failed to update document reference'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal isOpen={reference !== null} onClose={onClose} title="Edit Document Reference">
      <div className="space-y-4">
        {reference && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900">{reference.title}</p>
            {reference.original_filename && (
              <p className="text-sm text-gray-500">{reference.original_filename}</p>
            )}
          </div>
        )}

        <div>
          <label htmlFor="doc-type" className="block text-sm font-medium text-gray-700 mb-1">
            Document Type
          </label>
          <select
            id="doc-type"
            value={type}
            onChange={(e) => setType(e.target.value as DocumentType | '')}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Select a type...</option>
            <option value="contract">Contract</option>
            <option value="itinerary">Itinerary</option>
            <option value="confirmation">Confirmation</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="doc-notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            id="doc-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Add notes about this document..."
          />
        </div>

        <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={includeInReport}
            onChange={(e) => setIncludeInReport(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <span className="font-medium">Include in reports</span>
            <p className="text-sm text-gray-500">Include this document in expense reports</p>
          </div>
        </label>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} isLoading={isSaving}>
            Save Changes
          </Button>
        </div>
      </div>
    </Modal>
  )
}
