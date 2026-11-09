// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
const API_BASE = '/api/v1'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Return the server error message of an ApiError, else the fallback. */
export function errorMessage(e: unknown, fallback: string): string {
  return e instanceof ApiError && e.message ? e.message : fallback
}

/** Fetch with credentials and throw an ApiError carrying the server detail on failure. */
async function send(path: string, options?: RequestInit, fallback = 'Request failed') {
  const response = await fetch(`${API_BASE}${path}`, { ...options, credentials: 'include' })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = typeof error.detail === 'string' && error.detail ? error.detail : fallback
    throw new ApiError(response.status, detail)
  }

  return response
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await send(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  /** POST multipart form data; the browser sets the Content-Type boundary. */
  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const response = await send(path, { method: 'POST', body: formData }, 'Upload failed')
    return response.json()
  },
  /** Fetch a binary response (GET unless options say otherwise). */
  blob: async (path: string, options?: RequestInit): Promise<Blob> => {
    const response = await send(path, options, 'Download failed')
    return response.blob()
  },
}

function saveBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function downloadFile(path: string, filename: string, options?: RequestInit) {
  saveBlob(await api.blob(path, { method: 'POST', ...options }), filename)
}

export async function downloadBackup(password: string) {
  const response = await send(
    '/backup/create',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    },
    'Backup failed',
  )

  const blob = await response.blob()
  const contentDisposition = response.headers.get('content-disposition')
  const filename =
    contentDisposition?.match(/filename="(.+)"/)?.[1] ||
    `homeoffice_assistant_backup_${Date.now()}.tar.gz.enc`
  saveBlob(blob, filename)
}

function backupForm(file: File, password?: string): FormData {
  const formData = new FormData()
  formData.append('file', file)
  if (password) {
    formData.append('password', password)
  }
  return formData
}

export function uploadBackupForValidation(file: File, password?: string) {
  return api.upload<RestoreValidationResponse>('/backup/validate', backupForm(file, password))
}

export function performRestore(file: File, password?: string) {
  return api.upload<RestoreResponse>('/backup/restore', backupForm(file, password))
}

export function uploadCompanyLogo(companyId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return api.upload(`/companies/${companyId}/logo`, formData)
}

export function getCompanyLogoUrl(companyId: string): string {
  return `${API_BASE}/companies/${companyId}/logo`
}

// Todo Template API functions
import type {
  ApplyTemplatesRequest,
  ApplyTemplatesResponse,
  CompanyCalendar,
  CompanyCalendarCreate,
  CompanyCalendarUpdate,
  HolidayCalendar,
  HolidayCalendarCreate,
  HolidayCalendarUpdate,
  HolidayEntry,
  RestoreResponse,
  RestoreValidationResponse,
  SupportedCountriesResponse,
  TemplateSet,
  TemplateSetWithComputedDates,
  TodoTemplate,
  TodoTemplateCreate,
  TodoTemplateUpdate,
} from '../types'

export const todoTemplatesApi = {
  /** Get all template sets (global + user's) */
  getTemplateSets: () => api.get<TemplateSet[]>('/todo-templates'),

  /** Get all templates as a flat list */
  getAllTemplates: () => api.get<TodoTemplate[]>('/todo-templates/all'),

  /** Get a specific template */
  getTemplate: (id: string) => api.get<TodoTemplate>(`/todo-templates/${id}`),

  /** Create a new user template */
  createTemplate: (data: TodoTemplateCreate) => api.post<TodoTemplate>('/todo-templates', data),

  /** Update a user template */
  updateTemplate: (id: string, data: TodoTemplateUpdate) =>
    api.put<TodoTemplate>(`/todo-templates/${id}`, data),

  /** Delete a user template */
  deleteTemplate: (id: string) => api.delete<void>(`/todo-templates/${id}`),

  /** Get templates with computed due dates for an event */
  getTemplatesForEvent: (eventId: string) =>
    api.get<TemplateSetWithComputedDates[]>(`/events/${eventId}/todos/templates`),

  /** Apply selected templates to an event */
  applyTemplatesToEvent: (eventId: string, data: ApplyTemplatesRequest) =>
    api.post<ApplyTemplatesResponse>(`/events/${eventId}/todos/from-templates`, data),
}

// Company Calendar API functions
export const companyCalendarsApi = {
  /** Get all calendars for a company */
  getCalendars: (companyId: string) =>
    api.get<CompanyCalendar[]>(`/companies/${companyId}/calendars`),

  /** Get a specific calendar */
  getCalendar: (companyId: string, calendarId: string) =>
    api.get<CompanyCalendar>(`/companies/${companyId}/calendars/${calendarId}`),

  /** Create a new calendar connection */
  createCalendar: (companyId: string, data: CompanyCalendarCreate) =>
    api.post<CompanyCalendar>(`/companies/${companyId}/calendars`, data),

  /** Update a calendar connection */
  updateCalendar: (companyId: string, calendarId: string, data: CompanyCalendarUpdate) =>
    api.put<CompanyCalendar>(`/companies/${companyId}/calendars/${calendarId}`, data),

  /** Delete a calendar connection */
  deleteCalendar: (companyId: string, calendarId: string) =>
    api.delete<void>(`/companies/${companyId}/calendars/${calendarId}`),

  /** Trigger a sync for a calendar */
  syncCalendar: (companyId: string, calendarId: string) =>
    api.post<CompanyCalendar>(`/companies/${companyId}/calendars/${calendarId}/sync`),
}

// Holiday Calendar API functions
export const holidayCalendarsApi = {
  /** Get all holiday calendar configurations for the current user */
  getCalendars: () => api.get<HolidayCalendar[]>('/holiday-calendars'),

  /** Get a specific holiday calendar configuration */
  getCalendar: (calendarId: string) => api.get<HolidayCalendar>(`/holiday-calendars/${calendarId}`),

  /** Create a new holiday calendar configuration */
  createCalendar: (data: HolidayCalendarCreate) =>
    api.post<HolidayCalendar>('/holiday-calendars', data),

  /** Update a holiday calendar configuration */
  updateCalendar: (calendarId: string, data: HolidayCalendarUpdate) =>
    api.put<HolidayCalendar>(`/holiday-calendars/${calendarId}`, data),

  /** Delete a holiday calendar configuration */
  deleteCalendar: (calendarId: string) => api.delete<void>(`/holiday-calendars/${calendarId}`),

  /** Get all supported countries with subdivisions */
  getSupportedCountries: () => api.get<SupportedCountriesResponse>('/holiday-calendars/countries'),

  /** Get holidays for a date range (uses user's configured calendars) */
  getHolidays: (startDate: string, endDate: string) =>
    api.get<{ holidays: HolidayEntry[] }>(
      `/holiday-calendars/holidays?start_date=${startDate}&end_date=${endDate}`,
    ),

  /** Preview holidays for a country/subdivision before adding it */
  previewHolidays: (countryCode: string, subdivision?: string, year?: number) => {
    const params = new URLSearchParams({ country_code: countryCode })
    if (subdivision) params.append('subdivision', subdivision)
    if (year) params.append('year', year.toString())
    return api.get<HolidayEntry[]>(`/holiday-calendars/preview?${params.toString()}`)
  },
}
