import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus } from 'lucide-react'
import { api } from '@/api/client'
import type { Company, Event, EventStatus } from '@/types'
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
})

type EventForm = z.infer<typeof eventSchema>

const statusColors: Record<EventStatus, 'default' | 'warning' | 'success' | 'info'> = {
  draft: 'default',
  preparation: 'warning',
  active: 'info',
  completed: 'success',
  archived: 'default',
}

export function Events() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<Event[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [eventsData, companiesData] = await Promise.all([
          api.get<Event[]>('/events'),
          api.get<Company[]>('/companies'),
        ])
        setEvents(eventsData)
        setCompanies(companiesData)
      } catch {
        setError('Failed to load data')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [])

  const onSubmit = async (data: EventForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const event = await api.post<Event>('/events', {
        ...data,
        description: data.description || null,
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
                      {event.start_date} to {event.end_date}
                    </p>
                  </div>
                  <Badge variant={statusColors[event.status]}>{event.status}</Badge>
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
    </div>
  )
}
