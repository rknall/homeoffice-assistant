import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Plus, Trash2, Pencil, Mail, FileText, RefreshCw } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, downloadFile } from '@/api/client'
import type { Company, Document, Event, EventStatus, Expense, ExpenseReportPreview, EventCustomFieldChoices } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'

const expenseSchema = z.object({
  date: z.string().min(1, 'Date is required'),
  amount: z.string().min(1, 'Amount is required'),
  currency: z.string().min(1, 'Currency is required'),
  payment_type: z.enum(['cash', 'credit_card', 'company_card', 'prepaid', 'invoice', 'other']),
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
  const [isDeleteDocModalOpen, setIsDeleteDocModalOpen] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [isDeletingDocument, setIsDeletingDocument] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isEditSaving, setIsEditSaving] = useState(false)

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
    } catch {
      setError('Failed to load event')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [id])

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

  const openEmailModal = () => {
    setEmailAddress(event?.company_name ? '' : '')
    setEmailResult(null)
    setIsEmailModalOpen(true)
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

  const sendEmailReport = async () => {
    if (!id) return
    setIsSendingEmail(true)
    setEmailResult(null)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/events/${id}/expense-report/send`,
        { recipient_email: emailAddress || null }
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
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => navigate('/events')}
          className="flex items-center text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Events
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{event.name}</h1>
            <p className="text-gray-500">
              {event.company_name && (
                <span className="text-gray-600">{event.company_name} &middot; </span>
              )}
              {event.start_date} to {event.end_date}
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
                      <td className="py-3 px-4">{expense.date}</td>
                      <td className="py-3 px-4">{expense.description || '-'}</td>
                      <td className="py-3 px-4">
                        <Badge variant="default">{expense.category}</Badge>
                      </td>
                      <td className="py-3 px-4">{expense.payment_type}</td>
                      <td className="py-3 px-4 text-right font-medium">
                        {expense.amount.toFixed(2)} {expense.currency}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => deleteExpense(expense.id)}
                          className="text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
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
          ) : documents.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No documents found for this event. Documents are matched by the company's storage path and the event's custom field value in Paperless.
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
                  {documents.map((doc) => (
                    <tr key={doc.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{doc.title}</td>
                      <td className="py-3 px-4 text-gray-500 text-sm">{doc.original_file_name}</td>
                      <td className="py-3 px-4 text-gray-500">
                        {doc.created ? new Date(doc.created).toLocaleDateString() : '-'}
                      </td>
                      <td className="py-3 px-4 text-gray-500">
                        {doc.archive_serial_number || '-'}
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => openDeleteDocModal(doc)}
                          className="text-gray-400 hover:text-red-600"
                          title="Delete from Paperless"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Send the expense report to the specified email address. If no email is provided, it will be sent to the company's expense recipient email.
          </p>
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
            <Button onClick={sendEmailReport} isLoading={isSendingEmail}>
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
    </div>
  )
}
