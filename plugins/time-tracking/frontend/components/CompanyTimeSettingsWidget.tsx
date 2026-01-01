// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from 'react'
import { companySettingsApi } from '../api'
import type { CompanyTimeSettings, CompanyTimeSettingsUpdate } from '../types'

interface CompanyTimeSettingsWidgetProps {
  companyId: string
}

const COUNTRY_OPTIONS = [
  { code: 'AT', name: 'Austria', regions: ['1', '2', '3', '4', '5', '6', '7', '8', '9'] },
  { code: 'DE', name: 'Germany', regions: [] },
  { code: 'CH', name: 'Switzerland', regions: [] },
]

const AT_REGIONS: Record<string, string> = {
  '1': 'Burgenland',
  '2': 'Kärnten',
  '3': 'Niederösterreich',
  '4': 'Oberösterreich',
  '5': 'Salzburg',
  '6': 'Steiermark',
  '7': 'Tirol',
  '8': 'Vorarlberg',
  '9': 'Wien',
}

export function CompanyTimeSettingsWidget({ companyId }: CompanyTimeSettingsWidgetProps) {
  const [settings, setSettings] = useState<CompanyTimeSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState<CompanyTimeSettingsUpdate>({})

  const loadSettings = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await companySettingsApi.get(companyId)
      setSettings(data)
      if (data) {
        setFormData({
          country_code: data.country_code,
          region: data.region,
          standard_hours_per_day: data.standard_hours_per_day,
          standard_hours_per_week: data.standard_hours_per_week,
          default_break_minutes: data.default_break_minutes,
          vacation_days_per_year: data.vacation_days_per_year,
          max_carryover_days: data.max_carryover_days,
          comp_time_enabled: data.comp_time_enabled,
          time_rounding_enabled: data.time_rounding_enabled,
        })
      } else {
        // Default values for new settings
        setFormData({
          country_code: 'AT',
          region: null,
          standard_hours_per_day: 8,
          standard_hours_per_week: 40,
          default_break_minutes: 30,
          vacation_days_per_year: 25,
          max_carryover_days: 5,
          comp_time_enabled: true,
          time_rounding_enabled: true,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }, [companyId])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      if (settings) {
        const updated = await companySettingsApi.update(companyId, formData)
        setSettings(updated)
      } else {
        const created = await companySettingsApi.create(companyId, formData)
        setSettings(created)
      }
      setIsEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    if (settings) {
      setFormData({
        country_code: settings.country_code,
        region: settings.region,
        standard_hours_per_day: settings.standard_hours_per_day,
        standard_hours_per_week: settings.standard_hours_per_week,
        default_break_minutes: settings.default_break_minutes,
        vacation_days_per_year: settings.vacation_days_per_year,
        max_carryover_days: settings.max_carryover_days,
        comp_time_enabled: settings.comp_time_enabled,
        time_rounding_enabled: settings.time_rounding_enabled,
      })
    }
    setIsEditing(false)
    setError(null)
  }

  const selectedCountry = COUNTRY_OPTIONS.find((c) => c.code === formData.country_code)

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Time Tracking Settings</h3>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-4 bg-gray-200 rounded w-1/3" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Time Tracking Settings</h3>
        {!isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {settings ? 'Edit' : 'Configure'}
          </button>
        )}
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {isEditing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSave()
            }}
            className="space-y-4"
          >
            {/* Country and Region */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-1">
                  Country
                </label>
                <select
                  id="country"
                  value={formData.country_code || 'AT'}
                  onChange={(e) =>
                    setFormData({ ...formData, country_code: e.target.value, region: null })
                  }
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  {COUNTRY_OPTIONS.map((country) => (
                    <option key={country.code} value={country.code}>
                      {country.name}
                    </option>
                  ))}
                </select>
              </div>
              {selectedCountry?.regions.length ? (
                <div>
                  <label htmlFor="region" className="block text-sm font-medium text-gray-700 mb-1">
                    Region
                  </label>
                  <select
                    id="region"
                    value={formData.region || ''}
                    onChange={(e) => setFormData({ ...formData, region: e.target.value || null })}
                    className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="">All regions</option>
                    {selectedCountry.regions.map((region) => (
                      <option key={region} value={region}>
                        {AT_REGIONS[region] || region}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            {/* Working hours */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="hours-day" className="block text-sm font-medium text-gray-700 mb-1">
                  Standard Hours/Day
                </label>
                <input
                  type="number"
                  id="hours-day"
                  value={formData.standard_hours_per_day || 8}
                  onChange={(e) =>
                    setFormData({ ...formData, standard_hours_per_day: parseFloat(e.target.value) })
                  }
                  min="1"
                  max="12"
                  step="0.5"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="hours-week"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Standard Hours/Week
                </label>
                <input
                  type="number"
                  id="hours-week"
                  value={formData.standard_hours_per_week || 40}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      standard_hours_per_week: parseFloat(e.target.value),
                    })
                  }
                  min="1"
                  max="60"
                  step="0.5"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Break and vacation */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="break-mins"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Default Break (minutes)
                </label>
                <input
                  type="number"
                  id="break-mins"
                  value={formData.default_break_minutes || 30}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      default_break_minutes: parseInt(e.target.value, 10),
                    })
                  }
                  min="0"
                  max="120"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="vacation-days"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Vacation Days/Year
                </label>
                <input
                  type="number"
                  id="vacation-days"
                  value={formData.vacation_days_per_year || 25}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      vacation_days_per_year: parseInt(e.target.value, 10),
                    })
                  }
                  min="0"
                  max="50"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Carryover */}
            <div>
              <label htmlFor="carryover" className="block text-sm font-medium text-gray-700 mb-1">
                Max Carryover Days
              </label>
              <input
                type="number"
                id="carryover"
                value={formData.max_carryover_days || 5}
                onChange={(e) =>
                  setFormData({ ...formData, max_carryover_days: parseInt(e.target.value, 10) })
                }
                min="0"
                max="20"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              />
            </div>

            {/* Toggles */}
            <div className="space-y-3">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.comp_time_enabled ?? true}
                  onChange={(e) =>
                    setFormData({ ...formData, comp_time_enabled: e.target.checked })
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Enable comp time accrual</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.time_rounding_enabled ?? true}
                  onChange={(e) =>
                    setFormData({ ...formData, time_rounding_enabled: e.target.checked })
                  }
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Enable 5-minute rounding</span>
              </label>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        ) : settings ? (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <dt className="text-gray-500">Country</dt>
              <dd className="text-gray-900 font-medium">
                {COUNTRY_OPTIONS.find((c) => c.code === settings.country_code)?.name ||
                  settings.country_code}
                {settings.region && ` (${AT_REGIONS[settings.region] || settings.region})`}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Working Hours</dt>
              <dd className="text-gray-900 font-medium">
                {settings.standard_hours_per_day}h/day, {settings.standard_hours_per_week}h/week
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Default Break</dt>
              <dd className="text-gray-900 font-medium">{settings.default_break_minutes} min</dd>
            </div>
            <div>
              <dt className="text-gray-500">Vacation</dt>
              <dd className="text-gray-900 font-medium">
                {settings.vacation_days_per_year} days/year (max {settings.max_carryover_days}{' '}
                carryover)
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Comp Time</dt>
              <dd className="text-gray-900 font-medium">
                {settings.comp_time_enabled ? 'Enabled' : 'Disabled'}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Time Rounding</dt>
              <dd className="text-gray-900 font-medium">
                {settings.time_rounding_enabled ? 'Enabled (5 min)' : 'Disabled'}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-gray-500">
            No time tracking settings configured for this company.{' '}
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="text-blue-600 hover:text-blue-800"
            >
              Configure now
            </button>
          </p>
        )}
      </div>
    </div>
  )
}
