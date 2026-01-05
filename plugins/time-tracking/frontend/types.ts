// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Time Tracking Plugin TypeScript Types
 *
 * These types mirror the backend Pydantic schemas for type safety
 * across the frontend-backend boundary.
 *
 * Architecture: Single TimeEntry model (no TimeRecord container)
 * - Multiple entries per day per company allowed
 * - Each entry is a check-in/check-out pair or a full-day entry type
 */

export type Uuid = string

// Company info for unified view
export interface CompanyInfo {
  id: Uuid
  name: string
  color: string // Hex color for display
}

// Predefined company colors palette (used cyclically)
export const COMPANY_COLORS = [
  '#3B82F6', // blue-500
  '#10B981', // emerald-500
  '#8B5CF6', // violet-500
  '#F59E0B', // amber-500
  '#EF4444', // red-500
  '#06B6D4', // cyan-500
  '#EC4899', // pink-500
  '#6366F1', // indigo-500
]

// Entry types for time entries
export type EntryType =
  | 'work'
  | 'vacation'
  | 'sick'
  | 'doctor_visit'
  | 'public_holiday'
  | 'comp_time'
  | 'unpaid_leave'
  | 'parental_leave'
  | 'training'
  | 'other'

export const ENTRY_TYPE_LABELS: Record<EntryType, string> = {
  work: 'Work',
  vacation: 'Vacation',
  sick: 'Sick Leave',
  doctor_visit: 'Doctor Visit',
  public_holiday: 'Public Holiday',
  comp_time: 'Comp Time',
  unpaid_leave: 'Unpaid Leave',
  parental_leave: 'Parental Leave',
  training: 'Training',
  other: 'Other',
}

export const ENTRY_TYPE_COLORS: Record<EntryType, { bg: string; text: string }> = {
  work: { bg: 'bg-blue-100', text: 'text-blue-800' },
  vacation: { bg: 'bg-green-100', text: 'text-green-800' },
  sick: { bg: 'bg-red-100', text: 'text-red-800' },
  doctor_visit: { bg: 'bg-orange-100', text: 'text-orange-800' },
  public_holiday: { bg: 'bg-purple-100', text: 'text-purple-800' },
  comp_time: { bg: 'bg-cyan-100', text: 'text-cyan-800' },
  unpaid_leave: { bg: 'bg-gray-100', text: 'text-gray-800' },
  parental_leave: { bg: 'bg-pink-100', text: 'text-pink-800' },
  training: { bg: 'bg-indigo-100', text: 'text-indigo-800' },
  other: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

// Work location types
export type WorkLocation = 'office' | 'remote' | 'client_site' | 'travel'

export const WORK_LOCATION_LABELS: Record<WorkLocation, string> = {
  office: 'Office',
  remote: 'Remote',
  client_site: 'Client Site',
  travel: 'Travel',
}

// Compliance warning levels
export type WarningLevel = 'info' | 'warning' | 'error'

export const WARNING_LEVEL_COLORS: Record<
  WarningLevel,
  { bg: string; text: string; border: string }
> = {
  info: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  warning: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
    border: 'border-yellow-200',
  },
  error: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
}

// --- Time Entry Interfaces ---

/**
 * Individual time entry - the core time tracking record.
 * Each entry represents one of:
 * - A work session (check_in/check_out pair)
 * - A full-day absence (vacation, sick, etc.)
 * - A partial day (doctor visit with times)
 */
export interface TimeEntry {
  id: Uuid
  user_id: Uuid
  date: string // ISO date string (YYYY-MM-DD)
  company_id: Uuid | null
  company_name: string | null // For display
  entry_type: EntryType
  check_in: string | null // HH:MM format
  check_out: string | null // HH:MM format
  timezone: string | null
  work_location: WorkLocation | null
  notes: string | null
  submission_id: Uuid | null
  is_locked: boolean
  // Calculated fields
  is_open: boolean // True if checked in but not out
  gross_minutes: number | null
  gross_hours: number | null
  created_at: string
  updated_at: string
}

export interface TimeEntryCreate {
  date: string
  company_id?: Uuid | null
  entry_type?: EntryType
  check_in?: string | null
  check_out?: string | null
  timezone?: string | null
  work_location?: WorkLocation | null
  notes?: string | null
}

export interface TimeEntryUpdate {
  company_id?: Uuid | null
  entry_type?: EntryType
  check_in?: string | null
  check_out?: string | null
  timezone?: string | null
  work_location?: WorkLocation | null
  notes?: string | null
}

// Compliance warning interface
export interface ComplianceWarning {
  level: WarningLevel
  code: string
  message: string
  requires_explanation: boolean
  law_reference: string | null
}

// --- Daily Summary ---

/**
 * Aggregated data for a single day across all entries.
 */
export interface DailySummary {
  date: string
  entries: TimeEntry[]
  total_gross_hours: number
  total_net_hours: number
  break_minutes: number
  entry_count: number
  has_open_entry: boolean
  warnings: ComplianceWarning[]
}

// --- Leave Balance ---

export interface LeaveBalanceResponse {
  id: string
  user_id: string
  company_id: string | null
  year: number
  vacation_entitled: number
  vacation_carryover: number
  vacation_taken: number
  vacation_planned: number
  vacation_remaining: number
  comp_time_balance: number
  sick_days_taken: number
  created_at: string
  updated_at: string
}

// --- Company Time Settings ---

export interface CompanyTimeSettings {
  id: Uuid
  company_id: Uuid
  timezone: string
  country_code: string
  vacation_days_per_year: number
  daily_overtime_threshold: number
  weekly_overtime_threshold: number
  overtime_threshold_hours: number
  comp_time_warning_balance: number
  default_timesheet_contact_id: Uuid | null
  lock_period_days: number
  created_at: string
  updated_at: string
}

export interface CompanyTimeSettingsUpdate {
  timezone?: string
  country_code?: string
  vacation_days_per_year?: number
  daily_overtime_threshold?: number
  weekly_overtime_threshold?: number
  overtime_threshold_hours?: number
  comp_time_warning_balance?: number
  default_timesheet_contact_id?: Uuid | null
  lock_period_days?: number
}

// --- Holiday ---

export interface Holiday {
  date: string
  name: string
}

export interface CustomHoliday extends Holiday {
  id: Uuid
  user_id: Uuid
  company_id: Uuid | null
  created_at: string
  updated_at: string
}

// --- Check-in/out ---

export interface CheckInRequest {
  company_id?: Uuid | null
  work_location?: WorkLocation | null
  notes?: string | null
  timezone?: string | null
}

export interface CheckOutRequest {
  notes?: string | null
  timezone?: string | null
}

export interface CheckInStatusResponse {
  is_checked_in: boolean
  open_entry: TimeEntry | null
  today_entries: TimeEntry[]
  today_total_hours: number
}

// --- Reports ---

export interface MonthlyReportResponse {
  year: number
  month: number
  company_id: Uuid | null
  company_name: string | null
  user_name: string
  total_work_days: number
  total_gross_hours: number
  total_net_hours: number
  total_break_minutes: number
  overtime_hours: number
  vacation_days: number
  sick_days: number
  comp_time_days: number
  public_holiday_days: number
  entries: TimeEntry[]
  daily_summaries: DailySummary[]
}

// --- Plugin Info ---

export interface PluginInfoResponse {
  plugin_id: string
  plugin_name: string
  version: string
  entry_count: number
  current_balance: LeaveBalanceResponse | null
}

// ============================================================================
// Legacy type aliases for backward compatibility during migration
// These can be removed once all components are updated
// ============================================================================

/** @deprecated Use TimeEntry instead */
export type TimeRecord = TimeEntry

/** @deprecated Use EntryType instead */
export type DayType = EntryType

/** @deprecated Use ENTRY_TYPE_LABELS instead */
export const DAY_TYPE_LABELS = ENTRY_TYPE_LABELS

/** @deprecated Use ENTRY_TYPE_COLORS instead */
export const DAY_TYPE_COLORS = ENTRY_TYPE_COLORS

// ============================================================================
// Plugin Framework Types
// These types are required by the plugin system for integration with the host app
// ============================================================================

import type { ComponentType } from 'react'

/**
 * Plugin capabilities from manifest
 */
export interface PluginCapabilities {
  backend: boolean
  frontend: boolean
  config: boolean
}

/**
 * A permission provided by a plugin
 */
export interface ProvidedPermission {
  code: string
  description: string
}

/**
 * Plugin manifest metadata
 */
export interface PluginManifest {
  id: string
  name: string
  version: string
  description: string
  author?: string
  homepage?: string
  license?: string
  minHostVersion?: string
  maxHostVersion?: string
  capabilities: PluginCapabilities
  permissions: string[]
  required_permissions?: string[]
  provided_permissions?: ProvidedPermission[]
  dependencies?: string[]
}

/**
 * Navigation item provided by a plugin
 */
export interface PluginNavItem {
  id: string
  label: string
  icon?: string
  path: string
  order?: number
}

/**
 * Route definition provided by a plugin
 */
export interface PluginRoute {
  path: string
  component: ComponentType
  exact?: boolean
}

/**
 * Widget components that plugins can provide
 */
export interface PluginWidgets {
  dashboard?: ComponentType
  eventDetail?: ComponentType<{ eventId: string }>
  companyDetail?: ComponentType<{ companyId: string }>
}

/**
 * Frontend exports from a plugin module
 */
export interface PluginExports {
  manifest: PluginManifest
  getNavItems?: () => PluginNavItem[]
  getRoutes?: () => PluginRoute[]
  widgets?: PluginWidgets
  onLoad?: () => Promise<void>
  onUnload?: () => Promise<void>
}
