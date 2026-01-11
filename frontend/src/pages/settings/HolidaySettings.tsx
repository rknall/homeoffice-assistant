// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { holidayCalendarsApi } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { CountryInfo, HolidayCalendar, HolidayEntry } from '@/types'

export function HolidaySettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [calendars, setCalendars] = useState<HolidayCalendar[]>([])
  const [countries, setCountries] = useState<CountryInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Add modal state
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedCountry, setSelectedCountry] = useState<string>('')
  const [selectedSubdivision, setSelectedSubdivision] = useState<string>('')
  const [displayLabel, setDisplayLabel] = useState<string>('')
  const [previewHolidays, setPreviewHolidays] = useState<HolidayEntry[]>([])
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Holidays' }])
  }, [setBreadcrumb])

  const fetchData = useCallback(async () => {
    try {
      const [calendarsData, countriesData] = await Promise.all([
        holidayCalendarsApi.getCalendars(),
        holidayCalendarsApi.getSupportedCountries(),
      ])
      setCalendars(calendarsData)
      setCountries(countriesData.countries)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load holiday calendars')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const getSubdivisions = useCallback(() => {
    const country = countries.find((c) => c.code === selectedCountry)
    return country?.subdivisions || []
  }, [countries, selectedCountry])

  const handleCountryChange = (code: string) => {
    setSelectedCountry(code)
    setSelectedSubdivision('')
    const country = countries.find((c) => c.code === code)
    if (country) {
      setDisplayLabel(code)
    }
    setPreviewHolidays([])
  }

  const handleSubdivisionChange = (subdiv: string) => {
    setSelectedSubdivision(subdiv)
    if (subdiv) {
      setDisplayLabel(`${selectedCountry}-${subdiv}`)
    } else {
      setDisplayLabel(selectedCountry)
    }
  }

  const loadPreview = async () => {
    if (!selectedCountry) return

    setIsLoadingPreview(true)
    try {
      const preview = await holidayCalendarsApi.previewHolidays(
        selectedCountry,
        selectedSubdivision || undefined,
      )
      setPreviewHolidays(preview)
    } catch {
      setPreviewHolidays([])
    } finally {
      setIsLoadingPreview(false)
    }
  }

  useEffect(() => {
    if (selectedCountry) {
      loadPreview()
    }
  }, [selectedCountry, selectedSubdivision])

  const handleAdd = async () => {
    if (!selectedCountry || !displayLabel.trim()) return

    setIsSaving(true)
    try {
      await holidayCalendarsApi.createCalendar({
        country_code: selectedCountry,
        subdivision: selectedSubdivision || null,
        display_label: displayLabel.trim(),
      })
      setSuccess('Holiday calendar added successfully')
      setTimeout(() => setSuccess(null), 3000)
      setShowAddModal(false)
      resetModal()
      await fetchData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add holiday calendar')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    try {
      await holidayCalendarsApi.deleteCalendar(id)
      setSuccess('Holiday calendar removed successfully')
      setTimeout(() => setSuccess(null), 3000)
      await fetchData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to remove holiday calendar')
    } finally {
      setDeletingId(null)
    }
  }

  const resetModal = () => {
    setSelectedCountry('')
    setSelectedSubdivision('')
    setDisplayLabel('')
    setPreviewHolidays([])
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Holiday Settings</h1>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}
      {success && (
        <Alert variant="success" className="mb-4">
          {success}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Holiday Calendars</CardTitle>
            <Button
              size="sm"
              onClick={() => {
                resetModal()
                setShowAddModal(true)
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Country
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            Configure which national holidays appear in your calendar. Holidays are displayed with a
            gray background, similar to weekends.
          </p>

          {calendars.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No holiday calendars configured. Click "Add Country" to get started.
            </p>
          ) : (
            <div className="space-y-3">
              {calendars.map((calendar) => {
                const country = countries.find((c) => c.code === calendar.country_code)
                return (
                  <div
                    key={calendar.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <div className="font-medium text-gray-900">{calendar.display_label}</div>
                      <div className="text-sm text-gray-500">
                        {country?.name || calendar.country_code}
                        {calendar.subdivision && ` - ${calendar.subdivision}`}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(calendar.id)}
                      isLoading={deletingId === calendar.id}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Country Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false)
          resetModal()
        }}
        title="Add Holiday Calendar"
      >
        <div className="space-y-4">
          <Select
            label="Country"
            value={selectedCountry}
            onChange={(e) => handleCountryChange(e.target.value)}
            options={[
              { value: '', label: 'Select a country...' },
              ...countries.map((c) => ({ value: c.code, label: c.name })),
            ]}
          />

          {getSubdivisions().length > 0 && (
            <Select
              label="Region (optional)"
              value={selectedSubdivision}
              onChange={(e) => handleSubdivisionChange(e.target.value)}
              options={[
                { value: '', label: 'All regions' },
                ...getSubdivisions().map((s) => ({ value: s, label: s })),
              ]}
            />
          )}

          <div>
            <label htmlFor="display-label" className="block text-sm font-medium text-gray-700 mb-1">
              Display Label
            </label>
            <input
              id="display-label"
              type="text"
              value={displayLabel}
              onChange={(e) => setDisplayLabel(e.target.value)}
              maxLength={20}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., AT or DE-BY"
            />
            <p className="mt-1 text-xs text-gray-500">
              This label appears before holiday names in the calendar (e.g., "AT - Neujahr")
            </p>
          </div>

          {/* Holiday Preview */}
          {selectedCountry && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Holiday Preview ({new Date().getFullYear()})
              </label>
              <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-md p-2 bg-gray-50">
                {isLoadingPreview ? (
                  <div className="flex justify-center py-4">
                    <Spinner size="sm" />
                  </div>
                ) : previewHolidays.length > 0 ? (
                  <div className="space-y-1">
                    {previewHolidays.map((h) => (
                      <div key={`${h.date}-${h.name}`} className="text-sm text-gray-700">
                        <span className="font-medium">{h.date}</span> - {h.name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">No holidays found</p>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <Button
              variant="secondary"
              onClick={() => {
                setShowAddModal(false)
                resetModal()
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAdd}
              isLoading={isSaving}
              disabled={!selectedCountry || !displayLabel.trim()}
            >
              Add Calendar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
