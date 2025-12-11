// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ExternalLink, Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getCompanyLogoUrl } from '@/api/client'
import { CompanyContactsSection } from '@/components/CompanyContactsSection'
import { CompanyFormModal } from '@/components/CompanyFormModal'
import { ContactTypeBadge } from '@/components/ContactTypeBadge'
import { EmailTemplateEditor } from '@/components/EmailTemplateEditor'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type {
  Company,
  EmailTemplate,
  IntegrationConfig,
  StoragePath,
  TemplateReason,
  UUID,
} from '@/types'

export function CompanyDetail() {
  const { id } = useParams<{ id: UUID }>()
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [company, setCompany] = useState<Company | null>(null)
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [reasons, setReasons] = useState<TemplateReason[]>([])
  const [storagePaths, setStoragePaths] = useState<StoragePath[]>([])
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
    } catch {
      setError('Failed to load company')
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

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([
        fetchCompany(),
        fetchTemplates(),
        fetchReasons(),
        fetchStoragePaths(),
        checkSmtpIntegration(),
      ])
      setIsLoading(false)
    }
    loadData()
  }, [fetchCompany, fetchTemplates, fetchReasons, fetchStoragePaths, checkSmtpIntegration])

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
      !confirm(
        'Are you sure you want to delete this company? This will also delete all associated events, expenses, and email templates.',
      )
    ) {
      return
    }
    try {
      await api.delete(`/companies/${id}`)
      navigate('/companies')
    } catch {
      setError('Failed to delete company')
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
    if (!confirm('Are you sure you want to delete this email template?')) return
    try {
      await api.delete(`/email-templates/${templateId}`)
      await fetchTemplates()
    } catch {
      setError('Failed to delete template')
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
              {company.type === 'employer' ? 'Employer' : 'Third Party'}
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

      {/* Company Details Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Company Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {company.address && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500">Address</dt>
                <dd className="mt-1 text-gray-900 whitespace-pre-line">{company.address}</dd>
              </div>
            )}
            {company.country && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Country</dt>
                <dd className="mt-1 text-gray-900">{company.country}</dd>
              </div>
            )}
            {storagePaths.length > 0 && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Paperless Storage Path</dt>
                <dd className="mt-1 text-gray-900">
                  {storagePaths.find((sp) => sp.id === company.paperless_storage_path_id)?.name ||
                    '-'}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Contacts Section */}
      {id && (
        <div className="mb-6">
          <CompanyContactsSection
            companyId={id}
            contacts={company.contacts || []}
            onContactsChanged={fetchCompany}
          />
        </div>
      )}

      {/* Email Templates Card */}
      {!hasSmtpIntegration && (
        <Alert variant="warning" className="mb-4">
          No email integration has been configured. Email templates cannot be used until you{' '}
          <Link to="/settings/integrations" className="font-medium underline hover:no-underline">
            configure an SMTP server
          </Link>
          .
        </Alert>
      )}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Email Templates</CardTitle>
          <Button onClick={() => openTemplateModal()}>
            <Plus className="h-4 w-4 mr-2" />
            Add Template
          </Button>
        </CardHeader>
        <CardContent>
          {templates.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No company-specific email templates. This company will use global templates.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {templates.map((template) => (
                <div key={template.id} className="flex items-center justify-between py-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900">{template.name}</h3>
                    <p className="text-sm text-gray-500">
                      {template.reason === 'expense_report' && 'Expense Report'}
                      {template.is_default && ' (Default)'}
                    </p>
                    {template.contact_types && template.contact_types.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {template.contact_types.map((type) => (
                          <ContactTypeBadge key={type} type={type} size="sm" />
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    {template.is_default && <Badge variant="success">Default</Badge>}
                    <button
                      type="button"
                      onClick={() => openTemplateModal(template)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit template"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteTemplate(template.id)}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete template"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

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
