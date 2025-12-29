// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
export type Uuid = string

// User types
export interface User {
  id: Uuid
  username: string
  email: string
  is_active: boolean
  full_name: string | null
  avatar_url: string | null
  use_gravatar: boolean
  created_at: string
  updated_at: string
  permissions: string[]
  company_permissions: Record<string, string[]>
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

// Contact type enumeration for company contacts
export type ContactType =
  | 'billing'
  | 'hr'
  | 'technical'
  | 'support'
  | 'office'
  | 'sales'
  | 'management'
  | 'other'

export const CONTACT_TYPE_LABELS: Record<ContactType, string> = {
  billing: 'Billing',
  hr: 'HR',
  technical: 'Technical',
  support: 'Support',
  office: 'Office',
  sales: 'Sales',
  management: 'Management',
  other: 'Other',
}

// Company contact types
export interface CompanyContact {
  id: Uuid
  company_id: Uuid
  name: string
  email: string
  phone: string | null
  title: string | null
  department: string | null
  notes: string | null
  contact_types: ContactType[]
  is_main_contact: boolean
  created_at: string
  updated_at: string
}

export interface CompanyContactCreate {
  name: string
  email: string
  phone?: string | null
  title?: string | null
  department?: string | null
  notes?: string | null
  contact_types?: ContactType[]
  is_main_contact?: boolean
}

export interface CompanyContactUpdate {
  name?: string
  email?: string
  phone?: string | null
  title?: string | null
  department?: string | null
  notes?: string | null
  contact_types?: ContactType[]
  is_main_contact?: boolean
}

export interface Company {
  id: Uuid
  name: string
  type: CompanyType
  paperless_storage_path_id: number | null
  report_recipients: Array<{ name: string; email: string }> | null
  webpage: string | null
  address: string | null
  country: string | null
  logo_path: string | null
  contacts: CompanyContact[]
  created_at: string
  updated_at: string
}

export interface CompanyCreate {
  name: string
  type: CompanyType
  paperless_storage_path_id?: number | null
  report_recipients?: Array<{ name: string; email: string }> | null
  webpage?: string | null
  address?: string | null
  country?: string | null
}

export interface CompanyUpdate {
  name?: string
  type?: CompanyType
  paperless_storage_path_id?: number | null
  report_recipients?: Array<{ name: string; email: string }> | null
  webpage?: string | null
  address?: string | null
  country?: string | null
}

// Event types
// Note: status is computed from dates on the backend, not manually set
export type EventStatus = 'upcoming' | 'active' | 'past'

export interface Event {
  id: Uuid
  user_id: Uuid
  company_id: Uuid
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
  // Cover image fields
  cover_image_url: string | null
  cover_thumbnail_url: string | null
  cover_photographer_name: string | null
  cover_photographer_url: string | null
  cover_image_position_y: number | null
  created_at: string
  updated_at: string
  company_name?: string
}

export interface EventCreate {
  name: string
  description?: string | null
  company_id: Uuid
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
  // Cover image fields
  cover_image_url?: string | null
  cover_thumbnail_url?: string | null
  cover_photographer_name?: string | null
  cover_photographer_url?: string | null
  cover_image_position_y?: number | null
}

// Expense types
export type PaymentType =
  | 'cash'
  | 'credit_card'
  | 'debit_card'
  | 'company_card'
  | 'prepaid'
  | 'invoice'
  | 'other'
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
  id: Uuid
  event_id: Uuid
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
export type IntegrationType = 'paperless' | 'immich' | 'smtp' | 'unsplash'

export interface IntegrationConfig {
  id: Uuid
  integration_type: IntegrationType
  name: string
  is_active: boolean
  created_by: Uuid
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
  event_id: Uuid
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
  id: Uuid
  event_id: Uuid
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
  id: Uuid
  event_id: Uuid
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

export const TODO_CATEGORY_LABELS: Record<TodoCategory, string> = {
  travel: 'Travel',
  accommodation: 'Accommodation',
  preparation: 'Preparation',
  equipment: 'Equipment',
  contacts: 'Contacts',
  followup: 'Follow-up',
  other: 'Other',
}

export const TODO_CATEGORY_COLORS: Record<TodoCategory, { bg: string; text: string }> = {
  travel: { bg: 'bg-blue-100', text: 'text-blue-700' },
  accommodation: { bg: 'bg-purple-100', text: 'text-purple-700' },
  preparation: { bg: 'bg-green-100', text: 'text-green-700' },
  equipment: { bg: 'bg-gray-100', text: 'text-gray-700' },
  contacts: { bg: 'bg-cyan-100', text: 'text-cyan-700' },
  followup: { bg: 'bg-amber-100', text: 'text-amber-700' },
  other: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

export interface Todo {
  id: Uuid
  event_id: Uuid
  title: string
  description: string | null
  due_date: string | null
  completed: boolean
  category: TodoCategory
  created_at: string
  updated_at: string
}

export interface TodoCreate {
  title: string
  description?: string | null
  due_date?: string | null
  category?: TodoCategory
}

export interface TodoUpdate {
  title?: string
  description?: string | null
  due_date?: string | null
  completed?: boolean
  category?: TodoCategory
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
  id: Uuid
  name: string
  reason: string
  company_id: Uuid | null
  subject: string
  body_html: string
  body_text: string
  is_default: boolean
  contact_types: ContactType[]
  created_at: string
  updated_at: string
}

export interface EmailTemplateCreate {
  name: string
  reason: string
  company_id?: Uuid | null
  subject: string
  body_html: string
  body_text: string
  is_default?: boolean
  contact_types?: ContactType[]
}

export interface EmailTemplateUpdate {
  name?: string
  reason?: string
  subject?: string
  body_html?: string
  body_text?: string
  is_default?: boolean
  contact_types?: ContactType[]
}

// Template contact validation types
export interface TemplateContactValidation {
  is_valid: boolean
  missing_types: ContactType[]
  available_contacts: CompanyContact[]
  message: string
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
  event_id?: Uuid
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
  backup_format_version: string
  created_at: string | null
  created_by: string
  db_size_bytes: number
  avatar_count: number
  checksum: string
  is_password_protected: boolean
  has_legacy_secret_key: boolean
  integration_config_count: number
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
  migrations_run: boolean
  migrations_message: string
  configs_imported: number
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
  id: Uuid
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
  id: Uuid
  event_id: Uuid
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

// Unsplash types
export interface UnsplashUser {
  name: string
  username: string
  portfolio_url: string | null
}

export interface UnsplashUrls {
  raw: string
  full: string
  regular: string
  small: string
  thumb: string
}

export interface UnsplashLinks {
  html: string
  download_location: string
}

export interface UnsplashImage {
  id: string
  description: string | null
  width: number
  height: number
  color: string | null
  urls: UnsplashUrls
  user: UnsplashUser
  links: UnsplashLinks
}

export interface UnsplashSearchResponse {
  total: number
  total_pages: number
  results: UnsplashImage[]
}

// RBAC types
export interface Permission {
  code: string
  module: string
  description?: string
  /** If non-null, this permission is provided by a plugin */
  plugin_id?: string | null
}

export interface Role {
  id: Uuid
  name: string
  is_system: boolean
  description?: string
}

export interface RoleWithPermissions extends Role {
  permissions: Permission[]
}

export interface RoleCreate {
  name: string
  description?: string
  permissions: string[] // List of permission codes
}

export interface RoleUpdate {
  name?: string
  description?: string
  permissions?: string[]
}

export interface UserRole {
  user_id: Uuid
  role_id: Uuid
  company_id?: Uuid | null
  role: Role
}

export interface UserRoleAssignment {
  role_id: Uuid
  company_id?: Uuid | null
}

export interface UserPermissions {
  global_permissions: string[]
  company_permissions: Record<string, string[]>
}

// Dashboard types
export interface EventsByStatus {
  upcoming: number
  active: number
  past: number
}

export interface UpcomingEvent {
  id: Uuid
  name: string
  company_name: string | null
  start_date: string
  end_date: string
  city: string | null
  country: string | null
  days_until: number
}

export interface EventNeedingReport {
  event_id: Uuid
  event_name: string
  company_name: string | null
  expense_count: number
  total_amount: number
  currency: string
}

export interface IncompleteTodo {
  id: Uuid
  title: string
  due_date: string | null
  event_id: Uuid
  event_name: string
  is_overdue: boolean
}

export interface ExpenseByCategory {
  category: string
  amount: number
  percentage: number
}

export interface ExpenseSummary {
  total: number
  by_category: ExpenseByCategory[]
  period_days: number
}

export interface DashboardSummary {
  events_by_status: EventsByStatus
  upcoming_events: UpcomingEvent[]
  events_needing_reports: EventNeedingReport[]
  incomplete_todos: IncompleteTodo[]
  expense_summary: ExpenseSummary
}

// Event with summary (for enhanced event list)
export interface EventWithSummary extends Event {
  expense_count: number
  expense_total: number
  todo_count: number
  todo_incomplete_count: number
}
