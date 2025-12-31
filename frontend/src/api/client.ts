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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Request failed')
  }

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
}

export async function downloadFile(path: string, filename: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Download failed')
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function downloadBackup(password: string) {
  const response = await fetch(`${API_BASE}/backup/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Backup failed')
  }

  const blob = await response.blob()
  const contentDisposition = response.headers.get('content-disposition')
  const filename =
    contentDisposition?.match(/filename="(.+)"/)?.[1] ||
    `homeoffice_assistant_backup_${Date.now()}.tar.gz.enc`

  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export async function uploadBackupForValidation(file: File, password?: string) {
  const formData = new FormData()
  formData.append('file', file)
  if (password) {
    formData.append('password', password)
  }

  const response = await fetch(`${API_BASE}/backup/validate`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Validation failed')
  }

  return response.json()
}

export async function performRestore(file: File, password?: string) {
  const formData = new FormData()
  formData.append('file', file)
  if (password) {
    formData.append('password', password)
  }

  const response = await fetch(`${API_BASE}/backup/restore`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Restore failed')
  }

  return response.json()
}

export async function uploadCompanyLogo(companyId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/companies/${companyId}/logo`, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new ApiError(response.status, error.detail || 'Logo upload failed')
  }

  return response.json()
}

export function getCompanyLogoUrl(companyId: string): string {
  return `${API_BASE}/companies/${companyId}/logo`
}

// Todo Template API functions
import type {
  ApplyTemplatesRequest,
  ApplyTemplatesResponse,
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
