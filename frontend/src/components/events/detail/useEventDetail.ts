// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage } from '@/api/client'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useCompanies } from '@/stores/companies'
import type { Event, EventCustomFieldChoices, Expense, ExpenseReportPreview } from '@/types'
import { useEventCover } from './useEventCover'
import { useEventDocuments } from './useEventDocuments'

/** Loads one event with its expenses, report preview, documents and cover image. */
export function useEventDetail(id: string | undefined) {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const fetchCompanies = useCompanies((s) => s.fetchCompanies)
  const [event, setEvent] = useState<Event | null>(null)
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [preview, setPreview] = useState<ExpenseReportPreview | null>(null)
  const [customFieldChoices, setCustomFieldChoices] = useState<EventCustomFieldChoices | null>(null)
  const [hasLlmIntegration, setHasLlmIntegration] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const documents = useEventDocuments(id, expenses, setError)
  const cover = useEventCover(id, event, setEvent, setError)
  const { fetchDocuments, fetchDocumentReferences } = documents
  const { fetchLocationImage, setImagePosition } = cover

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      const [eventData, expensesData, previewData, , choicesData] = await Promise.all([
        api.get<Event>(`/events/${id}`),
        api.get<Expense[]>(`/events/${id}/expenses`),
        // Optional data: a failing call must not blank the page
        api.get<ExpenseReportPreview>(`/events/${id}/expense-report/preview`).catch(() => null),
        fetchCompanies(),
        api
          .get<EventCustomFieldChoices>('/integrations/event-custom-field-choices')
          .catch(() => null),
      ])
      setEvent(eventData)
      setExpenses(expensesData)
      setPreview(previewData)
      setCustomFieldChoices(choicesData)
      // Initialize cover image position
      setImagePosition(eventData.cover_image_position_y ?? 50)
      // Fetch documents and document references after main data
      fetchDocuments()
      fetchDocumentReferences()
      // Fetch location image if event has cover image or location
      if (eventData.cover_image_url || eventData.country) {
        fetchLocationImage(eventData)
      }
    } catch (e) {
      setError(errorMessage(e, 'Failed to load event'))
    } finally {
      setIsLoading(false)
    }
  }, [
    fetchCompanies,
    fetchDocuments,
    fetchDocumentReferences,
    fetchLocationImage,
    setImagePosition,
    id,
  ])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Check whether an active LLM integration exists (enables document scanning)
  useEffect(() => {
    api
      .get<{ is_active: boolean }[]>('/integrations?integration_type=llm')
      .then((configs) => setHasLlmIntegration(configs.some((c) => c.is_active)))
      .catch(() => setHasLlmIntegration(false))
  }, [])

  // Set breadcrumb when event data is loaded
  useEffect(() => {
    if (event) {
      const items: { label: string; href?: string }[] = [{ label: 'Events', href: '/events' }]
      if (event.company_name && event.company_id) {
        items.push({ label: event.company_name, href: `/companies/${event.company_id}` })
      }
      items.push({ label: event.name })
      setBreadcrumb(items)
    }
  }, [event, setBreadcrumb])

  return {
    event,
    expenses,
    preview,
    customFieldChoices,
    hasLlmIntegration,
    isLoading,
    error,
    setError,
    fetchData,
    documents,
    cover,
  }
}
