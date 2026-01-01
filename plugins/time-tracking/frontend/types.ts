// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Time Tracking Plugin TypeScript Types
 *
 * These types mirror the backend Pydantic schemas for type safety
 * across the frontend-backend boundary.
 */

export type Uuid = string

// Day types for time records
export type DayType =
  | 'work'
  | 'vacation'
  | 'sick'
  | 'doctor_visit'
  | 'public_holiday'
  | 'comp_time'
  | 'unpaid_leave'
  | 'weekend'

export const DAY_TYPE_LABELS: Record<DayType, string> = {
  work: 'Work',
  vacation: 'Vacation',
  sick: 'Sick Leave',
  doctor_visit: 'Doctor Visit',
  public_holiday: 'Public Holiday',
  comp_time: 'Comp Time',
  unpaid_leave: 'Unpaid Leave',
  weekend: 'Weekend',
}

export const DAY_TYPE_COLORS: Record<DayType, { bg: string; text: string }> = {
  work: { bg: 'bg-blue-100', text: 'text-blue-800' },
  vacation: { bg: 'bg-green-100', text: 'text-green-800' },
  sick: { bg: 'bg-red-100', text: 'text-red-800' },
  doctor_visit: { bg: 'bg-orange-100', text: 'text-orange-800' },
  public_holiday: { bg: 'bg-purple-100', text: 'text-purple-800' },
  comp_time: { bg: 'bg-cyan-100', text: 'text-cyan-800' },
  unpaid_leave: { bg: 'bg-gray-100', text: 'text-gray-800' },
  weekend: { bg: 'bg-gray-50', text: 'text-gray-600' },
}

// Leave balance types
export type LeaveType = 'vacation' | 'comp_time'

export const LEAVE_TYPE_LABELS: Record<LeaveType, string> = {
  vacation: 'Vacation',
  comp_time: 'Comp Time',
}

// Compliance warning levels
export type WarningLevel = 'info' | 'warning' | 'error'

export const WARNING_LEVEL_COLORS: Record<WarningLevel, { bg: string; text: string; border: string }> = {
  info: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  warning: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
  error: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
}

// Time record interfaces
export interface TimeRecord {
  id: Uuid
  user_id: Uuid
  company_id: Uuid
  date: string // ISO date string
  day_type: DayType
  check_in: string | null // HH:MM format
  check_out: string | null // HH:MM format
  break_minutes: number | null
  gross_hours: number | null
  net_hours: number | null
  comp_time_earned: number
  notes: string | null
  is_locked: boolean
  locked_at: string | null
  locked_by: Uuid | null
  created_at: string
  updated_at: string
}

export interface TimeRecordCreate {
  company_id: Uuid
  date: string
  day_type?: DayType
  check_in?: string | null
  check_out?: string | null
  break_minutes?: number | null
  notes?: string | null
}

export interface TimeRecordUpdate {
  day_type?: DayType
  check_in?: string | null
  check_out?: string | null
  break_minutes?: number | null
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

// Time record response with warnings
export interface TimeRecordWithWarnings {
  record: TimeRecord
  warnings: ComplianceWarning[]
}

// Leave balance interfaces
export interface LeaveBalance {
  id: Uuid
  user_id: Uuid
  company_id: Uuid
  year: number
  leave_type: LeaveType
  entitled_days: number
  carried_over: number
  used_days: number
  pending_days: number
  available_days: number // Computed property
  created_at: string
  updated_at: string
}

// Time allocation interfaces
export interface TimeAllocation {
  id: Uuid
  time_record_id: Uuid
  event_id: Uuid
  hours: number
  notes: string | null
  created_at: string
  updated_at: string
}

export interface TimeAllocationCreate {
  event_id: Uuid
  hours: number
  notes?: string | null
}

// Company time settings
export interface CompanyTimeSettings {
  id: Uuid
  company_id: Uuid
  country_code: string
  region: string | null
  standard_hours_per_day: number
  standard_hours_per_week: number
  default_break_minutes: number
  vacation_days_per_year: number
  max_carryover_days: number
  comp_time_enabled: boolean
  time_rounding_enabled: boolean
  created_at: string
  updated_at: string
}

export interface CompanyTimeSettingsCreate {
  country_code?: string
  region?: string | null
  standard_hours_per_day?: number
  standard_hours_per_week?: number
  default_break_minutes?: number
  vacation_days_per_year?: number
  max_carryover_days?: number
  comp_time_enabled?: boolean
  time_rounding_enabled?: boolean
}

export interface CompanyTimeSettingsUpdate {
  country_code?: string
  region?: string | null
  standard_hours_per_day?: number
  standard_hours_per_week?: number
  default_break_minutes?: number
  vacation_days_per_year?: number
  max_carryover_days?: number
  comp_time_enabled?: boolean
  time_rounding_enabled?: boolean
}

// Holiday interface
export interface Holiday {
  date: string
  name: string
  is_custom: boolean
}

// Monthly report interfaces
export interface MonthlyReportSummary {
  year: number
  month: number
  total_work_days: number
  total_work_hours: number
  total_overtime_hours: number
  total_comp_time_earned: number
  vacation_days_used: number
  sick_days: number
  public_holidays: number
}

// Check-in/out response
export interface CheckInOutResponse {
  record: TimeRecord
  message: string
}

// Week view data
export interface WeekData {
  start_date: string
  end_date: string
  records: TimeRecord[]
  total_hours: number
  warnings: ComplianceWarning[]
}

// API response types
export interface TimeRecordListResponse {
  records: TimeRecord[]
  total: number
}

export interface LeaveBalanceResponse {
  vacation: LeaveBalance | null
  comp_time: LeaveBalance | null
}
