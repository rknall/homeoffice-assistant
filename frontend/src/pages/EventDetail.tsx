import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Download, Plus, Trash2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, downloadFile } from '@/api/client'
import type { Event, Expense, ExpenseReportPreview } from '@/types'
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

export function EventDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [event, setEvent] = useState<Event | null>(null)
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [preview, setPreview] = useState<ExpenseReportPreview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

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

  const fetchData = async () => {
    if (!id) return
    try {
      const [eventData, expensesData, previewData] = await Promise.all([
        api.get<Event>(`/events/${id}`),
        api.get<Expense[]>(`/events/${id}/expenses`),
        api.get<ExpenseReportPreview>(`/events/${id}/expense-report/preview`),
      ])
      setEvent(eventData)
      setExpenses(expensesData)
      setPreview(previewData)
    } catch {
      setError('Failed to load event')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [id])

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
              {event.start_date} to {event.end_date}
            </p>
          </div>
          <Badge>{event.status}</Badge>
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
    </div>
  )
}
