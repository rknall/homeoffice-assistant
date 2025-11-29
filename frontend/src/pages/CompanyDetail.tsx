import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Pencil, Trash2, Plus, ArrowLeft } from 'lucide-react'
import { api } from '@/api/client'
import type { Company, IntegrationConfig, StoragePath, EmailTemplate, TemplateReason } from '@/types'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'
import { EmailTemplateEditor } from '@/components/EmailTemplateEditor'

const companySchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  type: z.enum(['employer', 'third_party']),
  expense_recipient_email: z.string().email().optional().or(z.literal('')),
  expense_recipient_name: z.string().max(200).optional(),
  paperless_storage_path_id: z.string().optional(),
})

type CompanyForm = z.infer<typeof companySchema>

const typeOptions = [
  { value: 'employer', label: 'Employer' },
  { value: 'third_party', label: 'Third Party' },
]

export function CompanyDetail() {
  const { id } = useParams<{ id: string }>()
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
  const [isSaving, setIsSaving] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CompanyForm>({
    resolver: zodResolver(companySchema),
  })

  const fetchCompany = async () => {
    if (!id) return
    try {
      const data = await api.get<Company>(`/companies/${id}`)
      setCompany(data)
    } catch {
      setError('Failed to load company')
    }
  }

  const fetchTemplates = async () => {
    if (!id) return
    try {
      // Get templates for this company (includes global templates)
      const data = await api.get<EmailTemplate[]>(`/email-templates?company_id=${id}`)
      // Filter to only company-specific templates
      setTemplates(data.filter(t => t.company_id === id))
    } catch {
      setTemplates([])
    }
  }

  const fetchReasons = async () => {
    try {
      const data = await api.get<TemplateReason[]>('/email-templates/reasons')
      setReasons(data)
    } catch {
      setReasons([])
    }
  }

  const fetchStoragePaths = async () => {
    try {
      const integrations = await api.get<IntegrationConfig[]>('/integrations?integration_type=paperless')
      const activeConfig = integrations.find(i => i.is_active)
      if (activeConfig) {
        const paths = await api.get<StoragePath[]>(`/integrations/${activeConfig.id}/storage-paths`)
        setStoragePaths(paths)
      }
    } catch {
      // Silently fail
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([
        fetchCompany(),
        fetchTemplates(),
        fetchReasons(),
        fetchStoragePaths(),
      ])
      setIsLoading(false)
    }
    loadData()
  }, [id])

  useEffect(() => {
    if (company) {
      setBreadcrumb([
        { label: 'Companies', href: '/companies' },
        { label: company.name },
      ])
    }
  }, [company, setBreadcrumb])

  const openEditModal = () => {
    if (!company) return
    reset({
      name: company.name,
      type: company.type,
      expense_recipient_email: company.expense_recipient_email || '',
      expense_recipient_name: company.expense_recipient_name || '',
      paperless_storage_path_id: company.paperless_storage_path_id?.toString() || '',
    })
    setIsEditModalOpen(true)
  }

  const onSubmit = async (data: CompanyForm) => {
    if (!id) return
    setIsSaving(true)
    setError(null)
    try {
      await api.put(`/companies/${id}`, {
        name: data.name,
        type: data.type,
        expense_recipient_email: data.expense_recipient_email || null,
        expense_recipient_name: data.expense_recipient_name || null,
        paperless_storage_path_id: data.paperless_storage_path_id
          ? parseInt(data.paperless_storage_path_id, 10)
          : null,
      })
      await fetchCompany()
      setIsEditModalOpen(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update company')
    } finally {
      setIsSaving(false)
    }
  }

  const deleteCompany = async () => {
    if (!id || !confirm('Are you sure you want to delete this company? This will also delete all associated events, expenses, and email templates.')) {
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
        <button
          onClick={() => navigate('/companies')}
          className="flex items-center text-gray-500 hover:text-gray-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Companies
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
            <p className="text-gray-500">
              {company.expense_recipient_email || 'No recipient email configured'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={company.type === 'employer' ? 'info' : 'default'}>
              {company.type === 'employer' ? 'Employer' : 'Third Party'}
            </Badge>
            <button
              onClick={openEditModal}
              className="p-2 text-gray-400 hover:text-gray-600"
              title="Edit company"
            >
              <Pencil className="h-5 w-5" />
            </button>
            <button
              onClick={deleteCompany}
              className="p-2 text-gray-400 hover:text-red-600"
              title="Delete company"
            >
              <Trash2 className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {/* Company Details Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Company Details</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Expense Recipient Name</dt>
              <dd className="mt-1 text-gray-900">{company.expense_recipient_name || '-'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Expense Recipient Email</dt>
              <dd className="mt-1 text-gray-900">{company.expense_recipient_email || '-'}</dd>
            </div>
            {storagePaths.length > 0 && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Paperless Storage Path</dt>
                <dd className="mt-1 text-gray-900">
                  {storagePaths.find(sp => sp.id === company.paperless_storage_path_id)?.name || '-'}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Email Templates Card */}
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
                <div
                  key={template.id}
                  className="flex items-center justify-between py-4"
                >
                  <div>
                    <h3 className="font-medium text-gray-900">{template.name}</h3>
                    <p className="text-sm text-gray-500">
                      {template.reason === 'expense_report' && 'Expense Report'}
                      {template.is_default && ' (Default)'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {template.is_default && (
                      <Badge variant="success">Default</Badge>
                    )}
                    <button
                      onClick={() => openTemplateModal(template)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit template"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
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
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Company"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Company Name"
            {...register('name')}
            error={errors.name?.message}
          />
          <Select
            label="Type"
            options={typeOptions}
            {...register('type')}
            error={errors.type?.message}
          />
          <Input
            label="Expense Recipient Email"
            type="email"
            {...register('expense_recipient_email')}
            error={errors.expense_recipient_email?.message}
          />
          <Input
            label="Expense Recipient Name"
            {...register('expense_recipient_name')}
            error={errors.expense_recipient_name?.message}
          />
          {storagePaths.length > 0 && (
            <Select
              label="Paperless Storage Path"
              options={[
                { value: '', label: 'None' },
                ...storagePaths.map((sp) => ({ value: sp.id.toString(), label: sp.name })),
              ]}
              {...register('paperless_storage_path_id')}
            />
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

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
