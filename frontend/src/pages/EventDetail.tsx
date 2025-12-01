// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Plus, Trash2, Pencil, Mail, FileText, RefreshCw, Receipt, MapPin, Camera } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, downloadFile } from '@/api/client'
import type { Company, Document, Event, EventStatus, Expense, ExpenseReportPreview, EventCustomFieldChoices, EmailTemplate, TemplatePreviewResponse, LocationImage } from '@/types'
import { PhotoGallery } from '@/components/PhotoGallery'
import { useLocale } from '@/stores/locale'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'
import { getPaymentTypeLabel, getCategoryLabel } from '@/utils/labels'

const expenseSchema = z.object({
  date: z.string().min(1, 'Date is required'),
  amount: z.string().min(1, 'Amount is required'),
  currency: z.string().min(1, 'Currency is required'),
  payment_type: z.enum(['cash', 'credit_card', 'debit_card', 'company_card', 'prepaid', 'invoice', 'other']),
  category: z.enum(['travel', 'accommodation', 'meals', 'transport', 'equipment', 'communication', 'other']),
  description: z.string().optional(),
})

type ExpenseForm = z.infer<typeof expenseSchema>

const eventSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  description: z.string().optional(),
  company_id: z.string().min(1, 'Company is required'),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  paperless_custom_field_value: z.string().optional(),
})

type EventForm = z.infer<typeof eventSchema>

const paymentTypeOptions = [
  { value: 'cash', label: 'Cash' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'debit_card', label: 'Debit Card' },
  { value: 'company_card', label: 'Company Card' },
  { value: 'prepaid', label: 'Prepaid' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'other', label: 'Other' },
]

const categoryOptions = [
  { value: 'travel', label: 'Travel' },
  { value: 'accommodation', label: 'Accommodation' },
  { value: 'meals', label: 'Meals' },
  { value: 'transport', label: 'Transport' },
  { value: 'equipment', label: 'Equipment' },
  { value: 'communication', label: 'Communication' },
  { value: 'other', label: 'Other' },
]

const statusColors: Record<EventStatus, 'default' | 'warning' | 'info'> = {
  planning: 'warning',
  active: 'info',
  past: 'default',
}

const statusLabels: Record<EventStatus, string> = {
  planning: 'Planning',
  active: 'Active',
  past: 'Past',
}

export function EventDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { formatDate } = useLocale()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [event, setEvent] = useState<Event | null>(null)
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [preview, setPreview] = useState<ExpenseReportPreview | null>(null)
  const [companies, setCompanies] = useState<Company[]>([])
  const [customFieldChoices, setCustomFieldChoices] = useState<EventCustomFieldChoices | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false)
  const [isSendingEmail, setIsSendingEmail] = useState(false)
  const [emailAddress, setEmailAddress] = useState('')
  const [emailResult, setEmailResult] = useState<{ success: boolean; message: string } | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [emailTemplates, setEmailTemplates] = useState<EmailTemplate[]>([])
  const [emailPreview, setEmailPreview] = useState<TemplatePreviewResponse | null>(null)
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [isLoadingEmailPreview, setIsLoadingEmailPreview] = useState(false)
  const [isDeleteDocModalOpen, setIsDeleteDocModalOpen] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [isDeletingDocument, setIsDeletingDocument] = useState(false)
  const [isDocExpenseModalOpen, setIsDocExpenseModalOpen] = useState(false)
  const [documentForExpense, setDocumentForExpense] = useState<Document | null>(null)
  const [documentPreviewUrl, setDocumentPreviewUrl] = useState<string | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isCreatingFromDoc, setIsCreatingFromDoc] = useState(false)
  const [isEditExpenseModalOpen, setIsEditExpenseModalOpen] = useState(false)
  const [expenseToEdit, setExpenseToEdit] = useState<Expense | null>(null)
  const [editExpensePreviewUrl, setEditExpensePreviewUrl] = useState<string | null>(null)
  const [isLoadingEditPreview, setIsLoadingEditPreview] = useState(false)
  const [isUpdatingExpense, setIsUpdatingExpense] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isEditSaving, setIsEditSaving] = useState(false)
  const [locationImage, setLocationImage] = useState<LocationImage | null>(null)
  const [photoCount, setPhotoCount] = useState(0)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExpenseForm>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      currency: 'EUR',
      payment_type: 'cash',
      category: 'other',
    },
  })

  const {
    register: registerEvent,
    handleSubmit: handleEventSubmit,
    reset: resetEvent,
    formState: { errors: eventErrors },
  } = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
  })

  const {
    register: registerDocExpense,
    handleSubmit: handleDocExpenseSubmit,
    reset: resetDocExpense,
    formState: { errors: docExpenseErrors },
  } = useForm<ExpenseForm>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      currency: 'EUR',
      payment_type: 'cash',
      category: 'other',
    },
  })

  const {
    register: registerEditExpense,
    handleSubmit: handleEditExpenseSubmit,
    reset: resetEditExpense,
    formState: { errors: editExpenseErrors },
  } = useForm<ExpenseForm>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      currency: 'EUR',
      payment_type: 'cash',
      category: 'other',
    },
  })

  // Filter documents to exclude those already linked to expenses
  const linkedDocIds = new Set(expenses.filter(e => e.paperless_doc_id).map(e => e.paperless_doc_id))
  const availableDocuments = documents.filter(doc => !linkedDocIds.has(doc.id))

  const fetchDocuments = async () => {
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
  }

  const fetchLocationImage = async (eventId: string) => {
    try {
      const image = await api.get<LocationImage | null>(`/events/${eventId}/location-image`)
      setLocationImage(image)
    } catch {
      // Location image is optional, ignore errors
      setLocationImage(null)
    }
  }

  const fetchData = async () => {
    if (!id) return
    try {
      const [eventData, expensesData, previewData, companiesData, choicesData] = await Promise.all([
        api.get<Event>(`/events/${id}`),
        api.get<Expense[]>(`/events/${id}/expenses`),
        api.get<ExpenseReportPreview>(`/events/${id}/expense-report/preview`),
        api.get<Company[]>('/companies'),
        api.get<EventCustomFieldChoices>('/integrations/event-custom-field-choices'),
      ])
      setEvent(eventData)
      setExpenses(expensesData)
      setPreview(previewData)
      setCompanies(companiesData)
      setCustomFieldChoices(choicesData)
      // Fetch documents after main data
      fetchDocuments()
      // Fetch location image if event has location
      if (eventData.country) {
        fetchLocationImage(id)
      }
    } catch {
      setError('Failed to load event')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [id])

  // Set breadcrumb when event data is loaded
  useEffect(() => {
    if (event) {
      const items: { label: string; href?: string }[] = [
        { label: 'Events', href: '/events' },
      ]
      if (event.company_name && event.company_id) {
        items.push({ label: event.company_name, href: `/companies/${event.company_id}` })
      }
      items.push({ label: event.name })
      setBreadcrumb(items)
    }
  }, [event, setBreadcrumb])

  const openEditModal = () => {
    if (!event) return
    resetEvent({
      name: event.name,
      description: event.description || '',
      company_id: event.company_id,
      start_date: event.start_date,
      end_date: event.end_date,
      paperless_custom_field_value: event.paperless_custom_field_value || '',
    })
    setIsEditModalOpen(true)
  }

  const onEventSubmit = async (data: EventForm) => {
    if (!id) return
    setIsEditSaving(true)
    setError(null)
    try {
      await api.put(`/events/${id}`, {
        ...data,
        description: data.description || null,
        paperless_custom_field_value: data.paperless_custom_field_value || null,
      })
      await fetchData()
      setIsEditModalOpen(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update event')
    } finally {
      setIsEditSaving(false)
    }
  }

  const deleteEvent = async () => {
    if (!id || !confirm('Are you sure you want to delete this event? This will also delete all associated expenses, contacts, notes, and todos.')) {
      return
    }
    try {
      await api.delete(`/events/${id}`)
      navigate('/events')
    } catch {
      setError('Failed to delete event')
    }
  }

  const onSubmit = async (data: ExpenseForm) => {
    if (!id) return
    setIsSaving(true)
    setError(null)
    try {
      await api.post(`/events/${id}/expenses`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
      })
      await fetchData()
      setIsModalOpen(false)
      reset()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create expense')
    } finally {
      setIsSaving(false)
    }
  }

  const deleteExpense = async (expenseId: string) => {
    if (!id || !confirm('Are you sure you want to delete this expense?')) return
    try {
      await api.delete(`/events/${id}/expenses/${expenseId}`)
      await fetchData()
    } catch {
      setError('Failed to delete expense')
    }
  }

  const generateReport = async () => {
    if (!id || !event) return
    setIsGenerating(true)
    try {
      const filename = `expense_report_${event.name.toLowerCase().replace(/\s+/g, '_')}.zip`
      await downloadFile(`/events/${id}/expense-report/generate`, filename)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate report')
    } finally {
      setIsGenerating(false)
    }
  }

  const openEmailModal = async () => {
    setEmailAddress('')
    setEmailResult(null)
    setSelectedTemplateId(null)
    setEmailPreview(null)
    setIsEmailModalOpen(true)

    // Fetch available templates
    setIsLoadingTemplates(true)
    try {
      const params = new URLSearchParams({ reason: 'expense_report' })
      if (event?.company_id) {
        params.append('company_id', event.company_id)
      }
      const templates = await api.get<EmailTemplate[]>(`/email-templates?${params.toString()}`)
      setEmailTemplates(templates)

      // Auto-select default template
      const defaultTemplate = templates.find(t =>
        t.company_id === event?.company_id && t.is_default
      ) || templates.find(t =>
        t.company_id === null && t.is_default
      ) || templates[0]

      if (defaultTemplate) {
        setSelectedTemplateId(defaultTemplate.id)
        loadEmailPreview(defaultTemplate)
      }
    } catch {
      setEmailTemplates([])
    } finally {
      setIsLoadingTemplates(false)
    }
  }

  const loadEmailPreview = async (template: EmailTemplate) => {
    if (!id) return
    setIsLoadingEmailPreview(true)
    try {
      const result = await api.post<TemplatePreviewResponse>('/email-templates/preview', {
        subject: template.subject,
        body_html: template.body_html,
        body_text: template.body_text,
        reason: template.reason,
        event_id: id,
      })
      setEmailPreview(result)
    } catch {
      setEmailPreview(null)
    } finally {
      setIsLoadingEmailPreview(false)
    }
  }

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplateId(templateId)
    const template = emailTemplates.find(t => t.id === templateId)
    if (template) {
      loadEmailPreview(template)
    } else {
      setEmailPreview(null)
    }
  }

  const openDeleteDocModal = (doc: Document) => {
    setDocumentToDelete(doc)
    setIsDeleteDocModalOpen(true)
  }

  const confirmDeleteDocument = async () => {
    if (!id || !documentToDelete) return
    setIsDeletingDocument(true)
    try {
      await api.delete(`/events/${id}/documents/${documentToDelete.id}`)
      await fetchDocuments()
      setIsDeleteDocModalOpen(false)
      setDocumentToDelete(null)
    } catch {
      setError('Failed to delete document')
    } finally {
      setIsDeletingDocument(false)
    }
  }

  const openDocExpenseModal = async (doc: Document) => {
    setDocumentForExpense(doc)
    setIsDocExpenseModalOpen(true)
    setIsLoadingPreview(true)

    // Pre-fill form with document data
    resetDocExpense({
      date: doc.created ? doc.created.split('T')[0] : new Date().toISOString().split('T')[0],
      amount: '',
      currency: 'EUR',
      payment_type: 'cash',
      category: 'other',
      description: doc.title,
    })

    // Load document preview
    try {
      const response = await fetch(`/api/v1/events/${id}/documents/${doc.id}/preview`, {
        credentials: 'include',
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        setDocumentPreviewUrl(url)
      }
    } catch {
      // Preview failed, continue without it
    } finally {
      setIsLoadingPreview(false)
    }
  }

  const closeDocExpenseModal = () => {
    setIsDocExpenseModalOpen(false)
    setDocumentForExpense(null)
    if (documentPreviewUrl) {
      URL.revokeObjectURL(documentPreviewUrl)
      setDocumentPreviewUrl(null)
    }
    resetDocExpense()
  }

  const onDocExpenseSubmit = async (data: ExpenseForm) => {
    if (!id || !documentForExpense) return
    setIsCreatingFromDoc(true)
    setError(null)
    try {
      await api.post(`/events/${id}/expenses`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
        paperless_doc_id: documentForExpense.id,
        original_filename: documentForExpense.original_file_name,
      })
      await fetchData()
      closeDocExpenseModal()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create expense')
    } finally {
      setIsCreatingFromDoc(false)
    }
  }

  const openEditExpenseModal = async (expense: Expense) => {
    setExpenseToEdit(expense)
    setIsEditExpenseModalOpen(true)

    // Pre-fill form with expense data
    resetEditExpense({
      date: expense.date,
      amount: String(expense.amount),
      currency: expense.currency,
      payment_type: expense.payment_type,
      category: expense.category,
      description: expense.description || '',
    })

    // Load document preview if expense has a linked document
    if (expense.paperless_doc_id) {
      setIsLoadingEditPreview(true)
      try {
        const response = await fetch(`/api/v1/events/${id}/documents/${expense.paperless_doc_id}/preview`, {
          credentials: 'include',
        })
        if (response.ok) {
          const blob = await response.blob()
          const url = URL.createObjectURL(blob)
          setEditExpensePreviewUrl(url)
        }
      } catch {
        // Preview failed, continue without it
      } finally {
        setIsLoadingEditPreview(false)
      }
    }
  }

  const closeEditExpenseModal = () => {
    setIsEditExpenseModalOpen(false)
    setExpenseToEdit(null)
    if (editExpensePreviewUrl) {
      URL.revokeObjectURL(editExpensePreviewUrl)
      setEditExpensePreviewUrl(null)
    }
    resetEditExpense()
  }

  const onEditExpenseSubmit = async (data: ExpenseForm) => {
    if (!id || !expenseToEdit) return
    setIsUpdatingExpense(true)
    setError(null)
    try {
      await api.put(`/events/${id}/expenses/${expenseToEdit.id}`, {
        ...data,
        amount: parseFloat(data.amount),
        description: data.description || null,
      })
      await fetchData()
      closeEditExpenseModal()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update expense')
    } finally {
      setIsUpdatingExpense(false)
    }
  }

  const sendEmailReport = async () => {
    if (!id) return
    setIsSendingEmail(true)
    setEmailResult(null)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/events/${id}/expense-report/send`,
        {
          recipient_email: emailAddress || null,
          template_id: selectedTemplateId,
        }
      )
      setEmailResult(result)
      if (result.success) {
        setTimeout(() => {
          setIsEmailModalOpen(false)
        }, 2000)
      }
    } catch (e) {
      setEmailResult({
        success: false,
        message: e instanceof Error ? e.message : 'Failed to send report',
      })
    } finally {
      setIsSendingEmail(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!event) {
    return (
      <div className="p-6">
        <Alert variant="error">Event not found</Alert>
      </div>
    )
  }

  return (
    <div>
      {/* Location Image Banner */}
      {locationImage && (
        <div className="relative mb-6 -mx-6 -mt-6 h-48 overflow-hidden">
          <img
            src={locationImage.image_url}
            alt={event.city ? `${event.city}, ${event.country}` : event.country || ''}
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
          <div className="absolute bottom-4 left-6 right-6">
            <h1 className="text-2xl font-bold text-white drop-shadow-lg">{event.name}</h1>
            <p className="text-white/90 drop-shadow">
              {event.company_name && (
                <span>{event.company_name} &middot; </span>
              )}
              {formatDate(event.start_date)} to {formatDate(event.end_date)}
              {(event.city || event.country) && (
                <span className="ml-2">
                  <MapPin className="inline h-4 w-4" /> {event.city ? `${event.city}, ${event.country}` : event.country}
                </span>
              )}
            </p>
          </div>
          <div className="absolute top-4 right-6 flex items-center gap-3">
            <Badge variant={statusColors[event.status]}>{statusLabels[event.status]}</Badge>
            <button
              onClick={openEditModal}
              className="p-2 text-white/80 hover:text-white bg-black/20 rounded-full"
              title="Edit event"
            >
              <Pencil className="h-5 w-5" />
            </button>
            <button
              onClick={deleteEvent}
              className="p-2 text-white/80 hover:text-red-400 bg-black/20 rounded-full"
              title="Delete event"
            >
              <Trash2 className="h-5 w-5" />
            </button>
          </div>
          {locationImage.attribution_html && (
            <div
              className="absolute bottom-1 right-2 text-xs text-white/60"
              dangerouslySetInnerHTML={{ __html: locationImage.attribution_html }}
            />
          )}
        </div>
      )}

      {/* Standard Header (no location image) */}
      {!locationImage && (
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{event.name}</h1>
              <p className="text-gray-500">
                {event.company_name && (
                  <span className="text-gray-600">{event.company_name} &middot; </span>
                )}
                {formatDate(event.start_date)} to {formatDate(event.end_date)}
                {(event.city || event.country) && (
                  <span className="ml-2 text-gray-600">
                    <MapPin className="inline h-4 w-4" /> {event.city ? `${event.city}, ${event.country}` : event.country}
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={statusColors[event.status]}>{statusLabels[event.status]}</Badge>
              <button
                onClick={openEditModal}
                className="p-2 text-gray-400 hover:text-gray-600"
                title="Edit event"
              >
                <Pencil className="h-5 w-5" />
              </button>
              <button
                onClick={deleteEvent}
                className="p-2 text-gray-400 hover:text-red-600"
                title="Delete event"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm font-medium text-gray-500">Total Expenses</p>
            <p className="text-2xl font-bold text-gray-900">
              {preview?.total.toFixed(2)} {preview?.currency}
            </p>
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

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Expenses</CardTitle>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={generateReport} isLoading={isGenerating}>
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
            <Button variant="secondary" onClick={openEmailModal}>
              <Mail className="h-4 w-4 mr-2" />
              Email Report
            </Button>
            <Button onClick={() => setIsModalOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Expense
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {expenses.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No expenses yet. Add your first expense to get started.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Date</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Description</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Category</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Payment</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Amount</th>
                    <th className="py-3 px-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((expense) => (
                    <tr key={expense.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">{formatDate(expense.date)}</td>
                      <td className="py-3 px-4">{expense.description || '-'}</td>
                      <td className="py-3 px-4">
                        <Badge variant="default">{getCategoryLabel(expense.category)}</Badge>
                      </td>
                      <td className="py-3 px-4">{getPaymentTypeLabel(expense.payment_type)}</td>
                      <td className="py-3 px-4 text-right font-medium">
                        {Number(expense.amount).toFixed(2)} {expense.currency}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEditExpenseModal(expense)}
                            className="text-gray-400 hover:text-blue-600"
                            title="Edit expense"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => deleteExpense(expense.id)}
                            className="text-gray-400 hover:text-red-600"
                            title="Delete expense"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Documents from Paperless
          </CardTitle>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchDocuments}
            isLoading={isLoadingDocuments}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoadingDocuments ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : availableDocuments.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              {documents.length === 0
                ? 'No documents found for this event. Documents are matched by the company\'s storage path and the event\'s custom field value in Paperless.'
                : 'All documents have been added as expenses.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Title</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Original Filename</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Created</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">ASN</th>
                    <th className="py-3 px-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {availableDocuments.map((doc) => (
                    <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{doc.title}</td>
                      <td className="py-3 px-4 text-gray-500 text-sm">{doc.original_file_name}</td>
                      <td className="py-3 px-4 text-gray-500">
                        {doc.created ? formatDate(doc.created) : '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-500">
                        {doc.archive_serial_number || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openDocExpenseModal(doc)}
                            className="text-gray-400 hover:text-blue-600"
                            title="Add as Expense"
                          >
                            <Receipt className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => openDeleteDocModal(doc)}
                            className="text-gray-400 hover:text-red-600"
                            title="Delete from Paperless"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            Photos from Immich
            {photoCount > 0 && (
              <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                {photoCount} linked
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <PhotoGallery
            eventId={id!}
            hasLocation={!!(event.latitude && event.longitude)}
            onPhotoCountChange={setPhotoCount}
          />
        </CardContent>
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          reset()
        }}
        title="Add Expense"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Date"
            type="date"
            {...register('date')}
            error={errors.date?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Amount"
              type="number"
              step="0.01"
              {...register('amount')}
              error={errors.amount?.message}
            />
            <Input
              label="Currency"
              {...register('currency')}
              error={errors.currency?.message}
            />
          </div>
          <Select
            label="Payment Type"
            options={paymentTypeOptions}
            {...register('payment_type')}
            error={errors.payment_type?.message}
          />
          <Select
            label="Category"
            options={categoryOptions}
            {...register('category')}
            error={errors.category?.message}
          />
          <Input
            label="Description"
            {...register('description')}
            error={errors.description?.message}
          />
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false)
                reset()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Add Expense
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          resetEvent()
        }}
        title="Edit Event"
        size="lg"
      >
        <form onSubmit={handleEventSubmit(onEventSubmit)} className="space-y-4">
          <Input
            label="Event Name"
            {...registerEvent('name')}
            error={eventErrors.name?.message}
          />
          <Input
            label="Description"
            {...registerEvent('description')}
            error={eventErrors.description?.message}
          />
          <Select
            label="Company"
            options={[
              { value: '', label: 'Select a company...' },
              ...companies.map((c) => ({ value: c.id, label: c.name })),
            ]}
            {...registerEvent('company_id')}
            error={eventErrors.company_id?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              {...registerEvent('start_date')}
              error={eventErrors.start_date?.message}
            />
            <Input
              label="End Date"
              type="date"
              {...registerEvent('end_date')}
              error={eventErrors.end_date?.message}
            />
          </div>
          {customFieldChoices?.available && (
            <Select
              label={`Paperless ${customFieldChoices.custom_field_name}`}
              options={[
                { value: '', label: `Select ${customFieldChoices.custom_field_name}...` },
                ...customFieldChoices.choices.map((c) => ({ value: c.value, label: c.label })),
              ]}
              {...registerEvent('paperless_custom_field_value')}
              error={eventErrors.paperless_custom_field_value?.message}
            />
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsEditModalOpen(false)
                resetEvent()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isEditSaving}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isEmailModalOpen}
        onClose={() => {
          setIsEmailModalOpen(false)
          setEmailResult(null)
        }}
        title="Email Expense Report"
        size="lg"
      >
        <div className="space-y-4">
          {/* Template Selection */}
          {isLoadingTemplates ? (
            <div className="flex items-center gap-2 py-4">
              <Spinner size="sm" />
              <span className="text-sm text-gray-500">Loading templates...</span>
            </div>
          ) : emailTemplates.length === 0 ? (
            <Alert variant="warning">
              No email templates found. Please configure a template in Settings or Company settings.
            </Alert>
          ) : (
            <Select
              label="Email Template"
              value={selectedTemplateId || ''}
              onChange={(e) => handleTemplateChange(e.target.value)}
              options={emailTemplates.map(t => ({
                value: t.id,
                label: `${t.name}${t.company_id ? '' : ' (Global)'}${t.is_default ? ' - Default' : ''}`,
              }))}
            />
          )}

          {/* Preview */}
          {selectedTemplateId && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                <p className="text-sm font-medium text-gray-700">Preview</p>
              </div>
              <div className="p-4 max-h-64 overflow-y-auto">
                {isLoadingEmailPreview ? (
                  <div className="flex items-center justify-center py-4">
                    <Spinner size="sm" />
                  </div>
                ) : emailPreview ? (
                  <div className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase">Subject</p>
                      <p className="text-gray-900">{emailPreview.subject}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase mb-1">Body</p>
                      <div
                        className="text-sm text-gray-700 prose prose-sm max-w-none"
                        dangerouslySetInnerHTML={{ __html: emailPreview.body_html }}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          )}

          <Input
            label="Recipient Email (optional)"
            type="email"
            value={emailAddress}
            onChange={(e) => setEmailAddress(e.target.value)}
            description="Leave empty to use company's expense recipient email"
          />

          {emailResult && (
            <Alert variant={emailResult.success ? 'success' : 'error'}>
              {emailResult.message}
            </Alert>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsEmailModalOpen(false)
                setEmailResult(null)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={sendEmailReport}
              isLoading={isSendingEmail}
              disabled={emailTemplates.length === 0 || !selectedTemplateId}
            >
              <Mail className="h-4 w-4 mr-2" />
              Send Report
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={isDeleteDocModalOpen}
        onClose={() => {
          setIsDeleteDocModalOpen(false)
          setDocumentToDelete(null)
        }}
        title="Delete Document"
      >
        <div className="space-y-4">
          <Alert variant="warning">
            This will permanently delete the document from Paperless-ngx. This action cannot be undone.
          </Alert>
          {documentToDelete && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="font-medium text-gray-900">{documentToDelete.title}</p>
              <p className="text-sm text-gray-500">{documentToDelete.original_file_name}</p>
            </div>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsDeleteDocModalOpen(false)
                setDocumentToDelete(null)
              }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={confirmDeleteDocument}
              isLoading={isDeletingDocument}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Document
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={isDocExpenseModalOpen}
        onClose={closeDocExpenseModal}
        title="Add Document as Expense"
        size="4xl"
      >
        <div className="flex gap-6" style={{ minHeight: '500px' }}>
          {/* Document Preview - Left Side */}
          <div className="flex-1 border rounded-lg overflow-hidden bg-gray-100">
            {isLoadingPreview ? (
              <div className="flex items-center justify-center h-full">
                <Spinner />
              </div>
            ) : documentPreviewUrl ? (
              <iframe
                src={documentPreviewUrl}
                className="w-full h-full"
                title="Document Preview"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Preview not available</p>
                </div>
              </div>
            )}
          </div>

          {/* Expense Form - Right Side */}
          <div className="w-80 flex-shrink-0">
            {documentForExpense && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-900 truncate" title={documentForExpense.title}>
                  {documentForExpense.title}
                </p>
                <p className="text-xs text-gray-500 truncate" title={documentForExpense.original_file_name}>
                  {documentForExpense.original_file_name}
                </p>
              </div>
            )}
            <form onSubmit={handleDocExpenseSubmit(onDocExpenseSubmit)} className="space-y-4">
              <Input
                label="Date"
                type="date"
                {...registerDocExpense('date')}
                error={docExpenseErrors.date?.message}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Amount"
                  type="number"
                  step="0.01"
                  {...registerDocExpense('amount')}
                  error={docExpenseErrors.amount?.message}
                />
                <Input
                  label="Currency"
                  {...registerDocExpense('currency')}
                  error={docExpenseErrors.currency?.message}
                />
              </div>
              <Select
                label="Payment Type"
                options={paymentTypeOptions}
                {...registerDocExpense('payment_type')}
                error={docExpenseErrors.payment_type?.message}
              />
              <Select
                label="Category"
                options={categoryOptions}
                {...registerDocExpense('category')}
                error={docExpenseErrors.category?.message}
              />
              <Input
                label="Description"
                {...registerDocExpense('description')}
                error={docExpenseErrors.description?.message}
              />
              <div className="flex justify-end gap-3 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={closeDocExpenseModal}
                >
                  Cancel
                </Button>
                <Button type="submit" isLoading={isCreatingFromDoc}>
                  <Receipt className="h-4 w-4 mr-2" />
                  Add Expense
                </Button>
              </div>
            </form>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={isEditExpenseModalOpen}
        onClose={closeEditExpenseModal}
        title="Edit Expense"
        size={expenseToEdit?.paperless_doc_id ? '4xl' : 'md'}
      >
        <div className={expenseToEdit?.paperless_doc_id ? 'flex gap-6' : ''} style={expenseToEdit?.paperless_doc_id ? { minHeight: '500px' } : undefined}>
          {/* Document Preview - Left Side (only if expense has linked document) */}
          {expenseToEdit?.paperless_doc_id && (
            <div className="flex-1 border rounded-lg overflow-hidden bg-gray-100">
              {isLoadingEditPreview ? (
                <div className="flex items-center justify-center h-full">
                  <Spinner />
                </div>
              ) : editExpensePreviewUrl ? (
                <iframe
                  src={editExpensePreviewUrl}
                  className="w-full h-full"
                  title="Document Preview"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <div className="text-center">
                    <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Preview not available</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Expense Form - Right Side (or full width if no document) */}
          <div className={expenseToEdit?.paperless_doc_id ? 'w-80 flex-shrink-0' : ''}>
            {expenseToEdit?.original_filename && (
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-900">Linked Document</p>
                <p className="text-xs text-gray-500 truncate" title={expenseToEdit.original_filename}>
                  {expenseToEdit.original_filename}
                </p>
              </div>
            )}
            <form onSubmit={handleEditExpenseSubmit(onEditExpenseSubmit)} className="space-y-4">
              <Input
                label="Date"
                type="date"
                {...registerEditExpense('date')}
                error={editExpenseErrors.date?.message}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  label="Amount"
                  type="number"
                  step="0.01"
                  {...registerEditExpense('amount')}
                  error={editExpenseErrors.amount?.message}
                />
                <Input
                  label="Currency"
                  {...registerEditExpense('currency')}
                  error={editExpenseErrors.currency?.message}
                />
              </div>
              <Select
                label="Payment Type"
                options={paymentTypeOptions}
                {...registerEditExpense('payment_type')}
                error={editExpenseErrors.payment_type?.message}
              />
              <Select
                label="Category"
                options={categoryOptions}
                {...registerEditExpense('category')}
                error={editExpenseErrors.category?.message}
              />
              <Input
                label="Description"
                {...registerEditExpense('description')}
                error={editExpenseErrors.description?.message}
              />
              <div className="flex justify-end gap-3 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={closeEditExpenseModal}
                >
                  Cancel
                </Button>
                <Button type="submit" isLoading={isUpdatingExpense}>
                  Save Changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      </Modal>
    </div>
  )
}
