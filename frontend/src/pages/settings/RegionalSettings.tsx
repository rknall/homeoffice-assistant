// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect, useState } from 'react'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useLocale } from '@/stores/locale'
import type { LocaleSettings } from '@/types'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'

const dateFormatOptions = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2025-11-29)' },
  { value: 'DD.MM.YYYY', label: 'DD.MM.YYYY (29.11.2025)' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (29/11/2025)' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (11/29/2025)' },
]

const timeFormatOptions = [
  { value: '24h', label: '24-hour (14:30)' },
  { value: '12h', label: '12-hour (2:30 PM)' },
]

const timezoneOptions = [
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'Europe/London' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin' },
  { value: 'Europe/Paris', label: 'Europe/Paris' },
  { value: 'Europe/Amsterdam', label: 'Europe/Amsterdam' },
  { value: 'Europe/Vienna', label: 'Europe/Vienna' },
  { value: 'Europe/Zurich', label: 'Europe/Zurich' },
  { value: 'America/New_York', label: 'America/New York' },
  { value: 'America/Chicago', label: 'America/Chicago' },
  { value: 'America/Denver', label: 'America/Denver' },
  { value: 'America/Los_Angeles', label: 'America/Los Angeles' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney' },
]

export function RegionalSettings() {
  const { settings: localeSettings, fetchSettings: fetchLocaleSettings, updateSettings: updateLocaleSettings, isLoaded: localeLoaded } = useLocale()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localeDateFormat, setLocaleDateFormat] = useState(localeSettings.date_format)
  const [localeTimeFormat, setLocaleTimeFormat] = useState(localeSettings.time_format)
  const [localeTimezone, setLocaleTimezone] = useState(localeSettings.timezone)

  useEffect(() => {
    setBreadcrumb([
      { label: 'Settings', href: '/settings' },
      { label: 'Regional' },
    ])
  }, [setBreadcrumb])

  useEffect(() => {
    if (!localeLoaded) {
      fetchLocaleSettings()
    }
  }, [localeLoaded, fetchLocaleSettings])

  useEffect(() => {
    if (localeLoaded) {
      setLocaleDateFormat(localeSettings.date_format)
      setLocaleTimeFormat(localeSettings.time_format)
      setLocaleTimezone(localeSettings.timezone)
    }
  }, [localeLoaded, localeSettings])

  const saveSettings = async () => {
    setIsSaving(true)
    setError(null)
    try {
      await updateLocaleSettings({
        date_format: localeDateFormat,
        time_format: localeTimeFormat,
        timezone: localeTimezone,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Regional Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Date and Time</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <Alert variant="error" className="mb-4">{error}</Alert>}
          <div className="space-y-4 max-w-md">
            <Select
              label="Date Format"
              options={dateFormatOptions}
              value={localeDateFormat}
              onChange={(e) => setLocaleDateFormat(e.target.value as LocaleSettings['date_format'])}
            />
            <Select
              label="Time Format"
              options={timeFormatOptions}
              value={localeTimeFormat}
              onChange={(e) => setLocaleTimeFormat(e.target.value as LocaleSettings['time_format'])}
            />
            <Select
              label="Timezone"
              options={timezoneOptions}
              value={localeTimezone}
              onChange={(e) => setLocaleTimezone(e.target.value)}
            />
            <div className="flex justify-end pt-2">
              <Button onClick={saveSettings} isLoading={isSaving}>
                Save Changes
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
