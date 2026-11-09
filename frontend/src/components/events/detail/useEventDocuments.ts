// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useState } from 'react'
import { api, errorMessage } from '@/api/client'
import { confirmAction } from '@/stores/confirm'
import type { Document, DocumentReference, DocumentReferenceCreate, Expense } from '@/types'

/** Paperless documents and document references of one event. */
export function useEventDocuments(
  id: string | undefined,
  expenses: Expense[],
  setError: (message: string | null) => void,
) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [documentReferences, setDocumentReferences] = useState<DocumentReference[]>([])
  const [isLoadingDocRefs, setIsLoadingDocRefs] = useState(false)
  const [isLinkingDocument, setIsLinkingDocument] = useState(false)

  // Documents already linked to expenses or as document references are not available
  const linkedDocIds = new Set([
    ...expenses.filter((e) => e.paperless_doc_id).map((e) => e.paperless_doc_id),
    ...documentReferences.map((d) => d.paperless_doc_id),
  ])
  const availableDocuments = documents.filter((doc) => !linkedDocIds.has(doc.id))

  const fetchDocuments = useCallback(async () => {
    if (!id) return
    setIsLoadingDocuments(true)
    try {
      const docsData = await api.get<Document[]>(`/events/${id}/documents`)
      setDocuments(docsData)
    } catch {
      // Documents may not be available if Paperless is not configured
      setDocuments([])
    } finally {
      setIsLoadingDocuments(false)
    }
  }, [id])

  const fetchDocumentReferences = useCallback(async () => {
    if (!id) return
    setIsLoadingDocRefs(true)
    try {
      const refs = await api.get<DocumentReference[]>(`/events/${id}/document-references`)
      setDocumentReferences(refs)
    } catch {
      setDocumentReferences([])
    } finally {
      setIsLoadingDocRefs(false)
    }
  }, [id])

  const linkDocumentAsReference = async (doc: Document) => {
    if (!id) return
    setIsLinkingDocument(true)
    try {
      const data: DocumentReferenceCreate = {
        paperless_doc_id: doc.id,
        title: doc.title,
        original_filename: doc.original_file_name,
      }
      await api.post(`/events/${id}/document-references`, data)
      await fetchDocumentReferences()
    } catch (e) {
      setError(errorMessage(e, 'Failed to link document'))
    } finally {
      setIsLinkingDocument(false)
    }
  }

  const unlinkDocumentReference = async (refId: string) => {
    if (
      !id ||
      !(await confirmAction({
        title: 'Unlink document',
        message: 'Are you sure you want to unlink this document?',
        confirmLabel: 'Unlink',
      }))
    )
      return
    try {
      await api.delete(`/events/${id}/document-references/${refId}`)
      await fetchDocumentReferences()
    } catch (e) {
      setError(errorMessage(e, 'Failed to unlink document'))
    }
  }

  return {
    documents,
    availableDocuments,
    isLoadingDocuments,
    documentReferences,
    isLoadingDocRefs,
    isLinkingDocument,
    fetchDocuments,
    fetchDocumentReferences,
    linkDocumentAsReference,
    unlinkDocumentReference,
  }
}
