// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// User types
export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user'
  is_admin: boolean
  is_active: boolean
  full_name: string | null
  avatar_url: string | null
  use_gravatar: boolean
  created_at: string
  updated_at: string
}

export interface AuthResponse {
  user: User
}

export interface AuthStatus {
  first_run: boolean
  registration_enabled: boolean
}

// Company types
export type CompanyType = 'employer' | 'third_party'

export interface Company {
  id: string
  name: string
  type: CompanyType
  paperless_storage_path_id: number | null
  expense_recipient_email: string | null
  expense_recipient_name: string | null
  report_recipients: Array<{ name: string; email: string }> | null
  created_at: string
  updated_at: string
}

export interface CompanyCreate {
  name: string
  type: CompanyType
  paperless_storage_path_id?: number | null
  expense_recipient_email?: string | null
  expense_recipient_name?: string | null
  report_recipients?: Array<{ name: string; email: string }> | null
}

// Event types
export type EventStatus = 'planning' | 'active' | 'past'

export interface Event {
  id: string
  user_id: string
  company_id: string
  name: string
  description: string | null
  start_date: string
  end_date: string
  status: EventStatus
  external_tag: string | null
  paperless_custom_field_value: string | null
  // Location fields
  city: string | null
  country: string | null
  country_code: string | null
  latitude: number | null
  longitude: number | null
  created_at: string
  updated_at: string
  company_name?: string
}

export interface EventCreate {
  name: string
  description?: string | null
  company_id: string
  start_date: string
  end_date: string
  status?: EventStatus
  paperless_custom_field_value?: string | null
  // Location fields
  city?: string | null
  country?: string | null
  country_code?: string | null
  latitude?: number | null
  longitude?: number | null
}

// Expense types
export type PaymentType = 'cash' | 'credit_card' | 'debit_card' | 'company_card' | 'prepaid' | 'invoice' | 'other'
export type ExpenseCategory =
  | 'travel'
  | 'accommodation'
  | 'meals'
  | 'transport'
  | 'equipment'
  | 'communication'
  | 'other'
export type ExpenseStatus = 'pending' | 'included' | 'reimbursed'

export interface Expense {
  id: string
  event_id: string
  paperless_doc_id: number | null
  date: string
  amount: number
  currency: string
  payment_type: PaymentType
  category: ExpenseCategory
  description: string | null
  status: ExpenseStatus
  original_filename: string | null
  created_at: string
  updated_at: string
}

export interface ExpenseCreate {
  date: string
  amount: number
  currency?: string
  payment_type: PaymentType
  category: ExpenseCategory
  description?: string | null
  paperless_doc_id?: number | null
  original_filename?: string | null
}

// Integration types
export type IntegrationType = 'paperless' | 'immich' | 'smtp'

export interface IntegrationConfig {
  id: string
  integration_type: IntegrationType
  name: string
  is_active: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface IntegrationTypeInfo {
  type: string
  name: string
  config_schema: Record<string, unknown>
}

export interface StoragePath {
  id: number
  name: string
  path: string
}

export interface Document {
  id: number
  title: string
  created: string | null
  added: string | null
  original_file_name: string
  correspondent: number | null
  document_type: number | null
  archive_serial_number: number | null
}

export interface CustomFieldChoice {
  label: string
  value: string
}

export interface EventCustomFieldChoices {
  available: boolean
  custom_field_name: string
  choices: CustomFieldChoice[]
}

// Report types
export interface ExpenseReportPreview {
  event_id: string
  event_name: string
  company_name: string | null
  start_date: string
  end_date: string
  expense_count: number
  documents_available: number
  total: number
  currency: string
  by_category: Record<string, number>
  by_payment_type: Record<string, number>
  paperless_configured: boolean
}

// Contact types
export interface Contact {
  id: string
  event_id: string
  name: string
  company: string | null
  role: string | null
  email: string | null
  phone: string | null
  notes: string | null
  met_on: string | null
  created_at: string
  updated_at: string
}

// Note types
export type NoteType = 'observation' | 'todo' | 'report_section'

export interface Note {
  id: string
  event_id: string
  content: string
  note_type: NoteType
  created_at: string
  updated_at: string
}

// Todo types
export type TodoCategory =
  | 'travel'
  | 'accommodation'
  | 'preparation'
  | 'equipment'
  | 'contacts'
  | 'followup'
  | 'other'

export interface Todo {
  id: string
  event_id: string
  title: string
  description: string | null
  due_date: string | null
  completed: boolean
  category: TodoCategory
  created_at: string
  updated_at: string
}

// Locale settings types
export type DateFormatType = 'YYYY-MM-DD' | 'DD.MM.YYYY' | 'DD/MM/YYYY' | 'MM/DD/YYYY'
export type TimeFormatType = '24h' | '12h'

export interface LocaleSettings {
  date_format: DateFormatType
  time_format: TimeFormatType
  timezone: string
}

// Email Template types
export interface EmailTemplate {
  id: string
  name: string
  reason: string
  company_id: string | null
  subject: string
  body_html: string
  body_text: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EmailTemplateCreate {
  name: string
  reason: string
  company_id?: string | null
  subject: string
  body_html: string
  body_text: string
  is_default?: boolean
}

export interface EmailTemplateUpdate {
  name?: string
  reason?: string
  subject?: string
  body_html?: string
  body_text?: string
  is_default?: boolean
}

export interface TemplateVariableInfo {
  variable: string
  description: string
  example: string
}

export interface TemplateReason {
  reason: string
  description: string
  variables: TemplateVariableInfo[]
}

export interface TemplatePreviewRequest {
  subject: string
  body_html: string
  body_text: string
  reason: string
  event_id?: string
}

export interface TemplatePreviewResponse {
  subject: string
  body_html: string
  body_text: string
}

// Backup types
export interface BackupInfo {
  database_exists: boolean
  database_size_bytes: number
  avatar_count: number
}

export interface BackupMetadata {
  version: string
  created_at: string
  created_by: string
  db_size_bytes: number
  avatar_count: number
  checksum: string
}

export interface RestoreValidationResponse {
  valid: boolean
  message: string
  metadata: BackupMetadata | null
  warnings: string[]
}

export interface RestoreResponse {
  success: boolean
  message: string
  requires_restart: boolean
}

// Location types
export interface LocationSuggestion {
  city: string | null
  country: string
  country_code: string
  latitude: number
  longitude: number
  display_name: string
}

export interface LocationImage {
  image_url: string
  thumbnail_url: string
  photographer_name: string | null
  photographer_url: string | null
  attribution_html: string | null
}

// Photo types
export interface PhotoAsset {
  id: string
  original_filename: string | null
  thumbnail_url: string | null
  taken_at: string | null
  latitude: number | null
  longitude: number | null
  city: string | null
  country: string | null
  distance_km: number | null
  is_linked: boolean
}

export interface PhotoReference {
  id: string
  event_id: string
  immich_asset_id: string
  caption: string | null
  include_in_report: boolean
  thumbnail_url: string | null
  taken_at: string | null
  latitude: number | null
  longitude: number | null
  created_at: string
  updated_at: string
}

export interface PhotoReferenceCreate {
  immich_asset_id: string
  caption?: string | null
  include_in_report?: boolean
  thumbnail_url?: string | null
  taken_at?: string | null
  latitude?: number | null
  longitude?: number | null
}

export interface PhotoReferenceUpdate {
  caption?: string | null
  include_in_report?: boolean
}
