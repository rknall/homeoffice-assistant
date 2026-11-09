// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { Document, DocumentReference } from '@/types'
import { AvailableDocumentsSection } from './AvailableDocumentsSection'
import { LinkedDocumentsSection } from './LinkedDocumentsSection'
import type { useEventDocuments } from './useEventDocuments'

interface DocumentsTabProps {
  eventId: string
  documents: ReturnType<typeof useEventDocuments>
  onEditReference: (reference: DocumentReference) => void
  onCreateExpense: (doc: Document) => void
}

/** Documents tab: linked document references and unlinked Paperless documents. */
export function DocumentsTab({
  eventId,
  documents,
  onEditReference,
  onCreateExpense,
}: DocumentsTabProps) {
  const previewDocument = (docId: number) => {
    window.open(`/api/v1/events/${eventId}/documents/${docId}/preview`, '_blank')
  }

  return (
    <>
      <LinkedDocumentsSection
        references={documents.documentReferences}
        isLoading={documents.isLoadingDocRefs}
        onPreview={previewDocument}
        onEdit={onEditReference}
        onUnlink={documents.unlinkDocumentReference}
      />

      {/* Divider */}
      <hr className="my-6 border-gray-200" />

      <AvailableDocumentsSection
        documents={documents.documents}
        availableDocuments={documents.availableDocuments}
        isLoading={documents.isLoadingDocuments}
        isLinking={documents.isLinkingDocument}
        onRefresh={documents.fetchDocuments}
        onPreview={previewDocument}
        onLink={documents.linkDocumentAsReference}
        onCreateExpense={onCreateExpense}
      />
    </>
  )
}
