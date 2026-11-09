// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ExternalLink, Pencil, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, companyCalendarsApi, errorMessage, getCompanyLogoUrl } from '@/api/client'
import { CalendarConnectionsSection } from '@/components/CalendarConnectionsSection'
import { CompanyContactsSection } from '@/components/CompanyContactsSection'
import { CompanyFormModal } from '@/components/CompanyFormModal'
import { EmailTemplateEditor } from '@/components/EmailTemplateEditor'
import { CompanyEmailTemplatesTab } from '@/components/settings/CompanyEmailTemplatesTab'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Tab, TabList, TabPanel, Tabs } from '@/components/ui/Tabs'
import { PluginWidgetSlot } from '@/plugins/PluginWidgetSlot'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { confirmAction } from '@/stores/confirm'
import type {
  Company,
  EmailTemplate,
  IntegrationConfig,
  StoragePath,
  TemplateReason,
  Uuid,
} from '@/types'
import { companyTypeLabels } from '@/utils/labels'

export function CompanyDetail() {
  const { id } = useParams<{ id: Uuid }>()
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [company, setCompany] = useState<Company | null>(null)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [reasons, setReasons] = useState<TemplateReason[]>([])
  const [storagePaths, setStoragePaths] = useState<StoragePath[]>([])
  const [eventCount, setEventCount] = useState(0)
  const [calendarCount, setCalendarCount] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hasSmtpIntegration, setHasSmtpIntegration] = useState(true)

  const fetchCompany = useCallback(async () => {
    if (!id) return
    try {
      const data = await api.get<Company>(`/companies/${id}`)
      setCompany(data)
    } catch (e) {
      setError(errorMessage(e, 'Failed to load company'))
    }
  }, [id])

  const fetchTemplates = useCallback(async () => {
    if (!id) return
    try {
      // Get templates for this company (includes global templates)
      const data = await api.get<EmailTemplate[]>(`/email-templates?company_id=${id}`)
      // Filter to only company-specific templates
      setTemplates(data.filter((t) => t.company_id === id))
    } catch {
      setTemplates([])
    }
  }, [id])

  const fetchReasons = useCallback(async () => {
    try {
      const data = await api.get<TemplateReason[]>('/email-templates/reasons')
      setReasons(data)
    } catch {
      setReasons([])
    }
  }, [])

  const fetchStoragePaths = useCallback(async () => {
    try {
      const integrations = await api.get<IntegrationConfig[]>(
        '/integrations?integration_type=paperless',
      )
      const activeConfig = integrations.find((i) => i.is_active)
      if (activeConfig) {
        const paths = await api.get<StoragePath[]>(`/integrations/${activeConfig.id}/storage-paths`)
        setStoragePaths(paths)
      }
    } catch {
      // Silently fail
    }
  }, [])

  const checkSmtpIntegration = useCallback(async () => {
    try {
      const integrations = await api.get<IntegrationConfig[]>('/integrations')
      setHasSmtpIntegration(integrations.some((i) => i.integration_type === 'smtp'))
    } catch {
      // Silently fail - assume configured
    }
  }, [])

  const fetchEventCount = useCallback(async () => {
    if (!id) return
    try {
      const data = await api.get<{ count: number }>(`/events/count?company_id=${id}`)
      setEventCount(data.count)
    } catch {
      setEventCount(0)
    }
  }, [id])

  const fetchCalendarCount = useCallback(async () => {
    if (!id) return
    try {
      const calendars = await companyCalendarsApi.getCalendars(id)
      setCalendarCount(calendars.length)
    } catch {
      setCalendarCount(0)
    }
  }, [id])

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([
        fetchCompany(),
        fetchTemplates(),
        fetchReasons(),
        fetchStoragePaths(),
        checkSmtpIntegration(),
        fetchEventCount(),
        fetchCalendarCount(),
      ])
      setIsLoading(false)
    }
    loadData()
  }, [
    fetchCompany,
    fetchTemplates,
    fetchReasons,
    fetchStoragePaths,
    checkSmtpIntegration,
    fetchEventCount,
    fetchCalendarCount,
  ])

  useEffect(() => {
    if (company) {
      setBreadcrumb([{ label: 'Companies', href: '/companies' }, { label: company.name }])
    }
  }, [company, setBreadcrumb])

  const handleCompanyUpdated = () => {
    fetchCompany()
    setIsEditModalOpen(false)
  }

  const deleteCompany = async () => {
    if (
      !id ||
      !(await confirmAction({
        title: 'Delete company',
        message:
          'Are you sure you want to delete this company? This will also delete all associated events, expenses, and email templates.',
        confirmLabel: 'Delete',
      }))
    ) {
      return
    }
    try {
      await api.delete(`/companies/${id}`)
      navigate('/companies')
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete company'))
    }
  }

  const openTemplateModal = (template?: EmailTemplate) => {
    setEditingTemplate(template || null)
    setIsTemplateModalOpen(true)
  }

  const closeTemplateModal = () => {
    setIsTemplateModalOpen(false)
    setEditingTemplate(null)
  }

  const handleTemplateSaved = () => {
    closeTemplateModal()
    fetchTemplates()
  }

  const deleteTemplate = async (templateId: string) => {
    if (
      !(await confirmAction({
        title: 'Delete email template',
        message: 'Are you sure you want to delete this email template?',
        confirmLabel: 'Delete',
      }))
    )
      return
    try {
      await api.delete(`/email-templates/${templateId}`)
      await fetchTemplates()
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete template'))
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!company) {
    return (
      <div className="p-6">
        <Alert variant="error">Company not found</Alert>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {company.logo_path && (
              <img
                src={getCompanyLogoUrl(company.id)}
                alt={`${company.name} logo`}
                className="h-16 w-16 object-contain rounded-lg border border-gray-200"
              />
            )}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
              {company.webpage && (
                <a
                  href={company.webpage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                >
                  {company.webpage}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={company.type === 'employer' ? 'info' : 'default'}>
              {companyTypeLabels[company.type]}
            </Badge>
            <button
              type="button"
              onClick={() => setIsEditModalOpen(true)}
              className="p-2 text-gray-400 hover:text-gray-600"
              title="Edit company"
            >
              <Pencil className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={deleteCompany}
              className="p-2 text-gray-400 hover:text-red-600"
              title="Delete company"
            >
              <Trash2 className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Summary Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-blue-200 p-4">
          <div className="text-sm text-blue-600">Total Events</div>
          <div className="text-2xl font-semibold text-gray-900">{eventCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Contacts</div>
          <div className="text-2xl font-semibold text-gray-900">
            {company.contacts?.length || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Connected Calendars</div>
          <div className="text-2xl font-semibold text-gray-900">{calendarCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Email Templates</div>
          <div className="text-2xl font-semibold text-gray-900">{templates.length}</div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultTab="general" className="mb-6">
        <TabList>
          <Tab value="general">General</Tab>
          <Tab value="contacts">Contacts</Tab>
          <Tab value="calendars">Connected Calendars</Tab>
          <Tab value="templates">Email Templates</Tab>
        </TabList>

        {/* General Tab */}
        <TabPanel value="general" className="bg-white rounded-b-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Company Details</h3>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <div>
              <dt className="text-sm text-gray-500">Address</dt>
              <dd className="mt-1 text-sm text-gray-900 whitespace-pre-line">
                {company.address || <span className="text-gray-400 italic">No address</span>}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500">Country</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {company.country || <span className="text-gray-400 italic">Not specified</span>}
              </dd>
            </div>
            {storagePaths.length > 0 && (
              <div>
                <dt className="text-sm text-gray-500">Paperless Storage Path</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {storagePaths.find((sp) => sp.id === company.paperless_storage_path_id)?.name ||
                    '-'}
                </dd>
              </div>
            )}
          </dl>
        </TabPanel>

        {/* Contacts Tab */}
        <TabPanel value="contacts" className="bg-white rounded-b-lg shadow">
          {id && (
            <CompanyContactsSection
              companyId={id}
              contacts={company.contacts || []}
              onContactsChanged={fetchCompany}
            />
          )}
        </TabPanel>

        {/* Connected Calendars Tab */}
        <TabPanel value="calendars" className="bg-white rounded-b-lg shadow">
          {id && (
            <CalendarConnectionsSection companyId={id} onCalendarsChanged={fetchCalendarCount} />
          )}
        </TabPanel>

        {/* Email Templates Tab */}
        <CompanyEmailTemplatesTab
          templates={templates}
          hasSmtpIntegration={hasSmtpIntegration}
          onAdd={() => openTemplateModal()}
          onEdit={openTemplateModal}
          onDelete={deleteTemplate}
        />
      </Tabs>

      {id && <PluginWidgetSlot companyId={id} />}

      {/* Edit Company Modal */}
      <CompanyFormModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSuccess={handleCompanyUpdated}
        company={company}
      />

      {/* Email Template Editor Modal */}
      <EmailTemplateEditor
        isOpen={isTemplateModalOpen}
        onClose={closeTemplateModal}
        onSaved={handleTemplateSaved}
        template={editingTemplate}
        companyId={id}
        reasons={reasons}
      />
    </div>
  )
}
