import { useEffect, useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, Pencil, ChevronDown } from 'lucide-react'
import { api } from '@/api/client'
import type { Company, Event, EventStatus, EventCustomFieldChoices as EventCustomFieldChoicesType } from '@/types'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'

const eventSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  description: z.string().optional(),
  company_id: z.string().min(1, 'Company is required'),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  paperless_custom_field_value: z.string().optional(),
})

type EventForm = z.infer<typeof eventSchema>

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

const validTransitions: Record<EventStatus, EventStatus[]> = {
  planning: ['active'],
  active: ['past', 'planning'],
  past: ['active'],
}

export function Events() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<Event[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [customFieldChoices, setCustomFieldChoices] = useState<EventCustomFieldChoicesType | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [statusDropdownOpen, setStatusDropdownOpen] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isEditSaving, setIsEditSaving] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
  })

  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
  })

  const fetchData = async () => {
    try {
      const [eventsData, companiesData, choicesData] = await Promise.all([
        api.get<Event[]>('/events'),
        api.get<Company[]>('/companies'),
        api.get<EventCustomFieldChoicesType>('/integrations/event-custom-field-choices'),
      ])
      setEvents(eventsData)
      setCompanies(companiesData)
      setCustomFieldChoices(choicesData)
    } catch {
      setError('Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const deleteEvent = async (e: React.MouseEvent, eventId: string) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this event? This will also delete all associated expenses, contacts, notes, and todos.')) {
      return
    }
    try {
      await api.delete(`/events/${eventId}`)
      await fetchData()
    } catch {
      setError('Failed to delete event')
    }
  }

  const openEditModal = (e: React.MouseEvent, event: Event) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingEvent(event)
    resetEdit({
      name: event.name,
      description: event.description || '',
      company_id: event.company_id,
      start_date: event.start_date,
      end_date: event.end_date,
      paperless_custom_field_value: event.paperless_custom_field_value || '',
    })
    setIsEditModalOpen(true)
  }

  const onEditSubmit = async (data: EventForm) => {
    if (!editingEvent) return
    setIsEditSaving(true)
    setError(null)
    try {
      await api.put(`/events/${editingEvent.id}`, {
        ...data,
        description: data.description || null,
        paperless_custom_field_value: data.paperless_custom_field_value || null,
      })
      await fetchData()
      setIsEditModalOpen(false)
      setEditingEvent(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update event')
    } finally {
      setIsEditSaving(false)
    }
  }

  const updateEventStatus = async (e: React.MouseEvent, eventId: string, newStatus: EventStatus) => {
    e.preventDefault()
    e.stopPropagation()
    setStatusDropdownOpen(null)
    try {
      await api.put(`/events/${eventId}`, { status: newStatus })
      await fetchData()
    } catch {
      setError('Failed to update status')
    }
  }

  const toggleStatusDropdown = (e: React.MouseEvent, eventId: string) => {
    e.preventDefault()
    e.stopPropagation()
    setStatusDropdownOpen(statusDropdownOpen === eventId ? null : eventId)
  }

  const onSubmit = async (data: EventForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const event = await api.post<Event>('/events', {
        ...data,
        description: data.description || null,
        paperless_custom_field_value: data.paperless_custom_field_value || null,
      })
      navigate(`/events/${event.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create event')
      setIsSaving(false)
    }
  }

  const companyOptions = [
    { value: '', label: 'Select a company...' },
    ...companies.map((c) => ({ value: c.id, label: c.name })),
  ]

  const customFieldOptions = customFieldChoices?.available
    ? [
        { value: '', label: `Select ${customFieldChoices.custom_field_name}...` },
        ...customFieldChoices.choices.map((c) => ({ value: c.value, label: c.label })),
      ]
    : []

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Event
        </Button>
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <Card>
        <CardHeader>
          <CardTitle>All Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : events.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No events yet. Create your first event to get started.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {events.map((event) => (
                <Link
                  key={event.id}
                  to={`/events/${event.id}`}
                  className="flex items-center justify-between py-4 hover:bg-gray-50 -mx-6 px-6 transition-colors"
                >
                  <div>
                    <h3 className="font-medium text-gray-900">{event.name}</h3>
                    <p className="text-sm text-gray-500">
                      {event.company_name && (
                        <span className="text-gray-600">{event.company_name} &middot; </span>
                      )}
                      {event.start_date} to {event.end_date}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="relative" ref={statusDropdownOpen === event.id ? dropdownRef : null}>
                      <button
                        onClick={(e) => toggleStatusDropdown(e, event.id)}
                        className="flex items-center gap-1"
                      >
                        <Badge variant={statusColors[event.status]}>
                          {statusLabels[event.status]}
                        </Badge>
                        <ChevronDown className="h-3 w-3 text-gray-400" />
                      </button>
                      {statusDropdownOpen === event.id && (
                        <div className="absolute right-0 mt-1 w-32 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                          {validTransitions[event.status].map((status) => (
                            <button
                              key={status}
                              onClick={(e) => updateEventStatus(e, event.id, status)}
                              className="block w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                            >
                              {statusLabels[status]}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <button
                      onClick={(e) => openEditModal(e, event)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit event"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      onClick={(e) => deleteEvent(e, event.id)}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete event"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </Link>
              ))}
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
        title="Create New Event"
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Event Name"
            {...register('name')}
            error={errors.name?.message}
          />
          <Input
            label="Description"
            {...register('description')}
            error={errors.description?.message}
          />
          <Select
            label="Company"
            options={companyOptions}
            {...register('company_id')}
            error={errors.company_id?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              {...register('start_date')}
              error={errors.start_date?.message}
            />
            <Input
              label="End Date"
              type="date"
              {...register('end_date')}
              error={errors.end_date?.message}
            />
          </div>
          {customFieldChoices?.available && (
            <Select
              label={`Paperless ${customFieldChoices.custom_field_name}`}
              options={customFieldOptions}
              {...register('paperless_custom_field_value')}
              error={errors.paperless_custom_field_value?.message}
            />
          )}
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
              Create Event
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          setEditingEvent(null)
          resetEdit()
        }}
        title="Edit Event"
        size="lg"
      >
        <form onSubmit={handleEditSubmit(onEditSubmit)} className="space-y-4">
          <Input
            label="Event Name"
            {...registerEdit('name')}
            error={editErrors.name?.message}
          />
          <Input
            label="Description"
            {...registerEdit('description')}
            error={editErrors.description?.message}
          />
          <Select
            label="Company"
            options={companyOptions}
            {...registerEdit('company_id')}
            error={editErrors.company_id?.message}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Start Date"
              type="date"
              {...registerEdit('start_date')}
              error={editErrors.start_date?.message}
            />
            <Input
              label="End Date"
              type="date"
              {...registerEdit('end_date')}
              error={editErrors.end_date?.message}
            />
          </div>
          {customFieldChoices?.available && (
            <Select
              label={`Paperless ${customFieldChoices.custom_field_name}`}
              options={customFieldOptions}
              {...registerEdit('paperless_custom_field_value')}
              error={editErrors.paperless_custom_field_value?.message}
            />
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsEditModalOpen(false)
                setEditingEvent(null)
                resetEdit()
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
    </div>
  )
}
