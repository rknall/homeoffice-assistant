// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { companyCalendarsApi } from '@/api/client'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import type { CalendarType, CompanyCalendar } from '@/types'
import { CALENDAR_TYPE_LABELS } from '@/types'

const PRESET_COLORS = [
  '#3B82F6', // blue
  '#EF4444', // red
  '#22C55E', // green
  '#F59E0B', // amber
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
]

const calendarSchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  calendar_type: z.enum(['google', 'outlook', 'ical']),
  external_id: z.string().min(1, 'Calendar ID or URL is required').max(500),
  color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Invalid color format'),
  sync_interval_minutes: z.number().min(5).max(1440),
  is_active: z.boolean(),
})

type CalendarFormData = z.infer<typeof calendarSchema>

interface CalendarFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  companyId: string
  calendar?: CompanyCalendar | null
}

export function CalendarFormModal({
  isOpen,
  onClose,
  onSuccess,
  companyId,
  calendar,
}: CalendarFormModalProps) {
  const isEditMode = !!calendar
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CalendarFormData>({
    resolver: zodResolver(calendarSchema),
    mode: 'onBlur',
    defaultValues: {
      name: '',
      calendar_type: 'google',
      external_id: '',
      color: '#3B82F6',
      sync_interval_minutes: 30,
      is_active: true,
    },
  })

  const selectedColor = watch('color')
  const selectedType = watch('calendar_type')

  useEffect(() => {
    if (isOpen) {
      if (calendar) {
        reset({
          name: calendar.name,
          calendar_type: calendar.calendar_type,
          external_id: calendar.external_id,
          color: calendar.color,
          sync_interval_minutes: calendar.sync_interval_minutes,
          is_active: calendar.is_active,
        })
      } else {
        reset({
          name: '',
          calendar_type: 'google',
          external_id: '',
          color: '#3B82F6',
          sync_interval_minutes: 30,
          is_active: true,
        })
      }
      setError(null)
    }
  }, [isOpen, calendar, reset])

  const handleClose = () => {
    onClose()
  }

  const onSubmit = async (data: CalendarFormData) => {
    setIsSaving(true)
    setError(null)

    try {
      if (isEditMode && calendar) {
        await companyCalendarsApi.updateCalendar(companyId, calendar.id, {
          name: data.name,
          external_id: data.external_id,
          color: data.color,
          sync_interval_minutes: data.sync_interval_minutes,
          is_active: data.is_active,
        })
      } else {
        await companyCalendarsApi.createCalendar(companyId, {
          name: data.name,
          calendar_type: data.calendar_type as CalendarType,
          external_id: data.external_id,
          color: data.color,
          sync_interval_minutes: data.sync_interval_minutes,
          is_active: data.is_active,
        })
      }

      onSuccess()
      handleClose()
    } catch (e) {
      setError(
        e instanceof Error ? e.message : `Failed to ${isEditMode ? 'update' : 'connect'} calendar`,
      )
    } finally {
      setIsSaving(false)
    }
  }

  const getExternalIdLabel = (): string => {
    switch (selectedType) {
      case 'google':
        return 'Calendar ID'
      case 'outlook':
        return 'Calendar ID'
      case 'ical':
        return 'iCal URL'
      default:
        return 'Calendar ID'
    }
  }

  const getExternalIdPlaceholder = (): string => {
    switch (selectedType) {
      case 'google':
        return 'e.g., example@gmail.com or calendar-id@group.calendar.google.com'
      case 'outlook':
        return 'e.g., calendar-id from Outlook'
      case 'ical':
        return 'e.g., https://calendar.example.com/feed.ics'
      default:
        return ''
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditMode ? 'Edit Calendar' : 'Connect Calendar'}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{error}</div>}

        <Input label="Display Name" {...register('name')} error={errors.name?.message} />

        {!isEditMode && (
          <Controller
            name="calendar_type"
            control={control}
            render={({ field }) => (
              <Select
                label="Calendar Type"
                value={field.value}
                onChange={field.onChange}
                options={[
                  { value: 'google', label: CALENDAR_TYPE_LABELS.google },
                  { value: 'outlook', label: CALENDAR_TYPE_LABELS.outlook },
                  { value: 'ical', label: CALENDAR_TYPE_LABELS.ical },
                ]}
                error={errors.calendar_type?.message}
              />
            )}
          />
        )}

        <Input
          label={getExternalIdLabel()}
          placeholder={getExternalIdPlaceholder()}
          {...register('external_id')}
          error={errors.external_id?.message}
        />

        {/* Color picker */}
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-2">Display Color</span>
          <div className="flex items-center gap-2">
            {PRESET_COLORS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setValue('color', color)}
                className={`w-8 h-8 rounded-full border-2 transition-all ${
                  selectedColor === color
                    ? 'border-gray-900 ring-2 ring-offset-2 ring-gray-400'
                    : 'border-white shadow hover:scale-110'
                }`}
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
            <Input
              className="w-24 ml-2"
              {...register('color')}
              error={errors.color?.message}
            />
          </div>
        </div>

        {/* Sync interval */}
        <Controller
          name="sync_interval_minutes"
          control={control}
          render={({ field }) => (
            <Select
              label="Sync Interval"
              value={String(field.value)}
              onChange={(value) => field.onChange(Number(value))}
              options={[
                { value: '5', label: 'Every 5 minutes' },
                { value: '15', label: 'Every 15 minutes' },
                { value: '30', label: 'Every 30 minutes' },
                { value: '60', label: 'Every hour' },
                { value: '360', label: 'Every 6 hours' },
                { value: '1440', label: 'Once a day' },
              ]}
              error={errors.sync_interval_minutes?.message}
            />
          )}
        />

        {/* Active toggle */}
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="calendar-active"
            {...register('is_active')}
            className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="calendar-active" className="text-sm text-gray-700">
            Enable automatic sync
          </label>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            {isEditMode ? 'Save Changes' : 'Connect Calendar'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
