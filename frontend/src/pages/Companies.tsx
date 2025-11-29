import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, ChevronRight } from 'lucide-react'
import { api } from '@/api/client'
import type { Company, IntegrationConfig, StoragePath } from '@/types'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'

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

export function Companies() {
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [storagePaths, setStoragePaths] = useState<StoragePath[]>([])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CompanyForm>({
    resolver: zodResolver(companySchema),
    defaultValues: {
      type: 'employer',
    },
  })

  const fetchCompanies = async () => {
    try {
      const data = await api.get<Company[]>('/companies')
      setCompanies(data)
    } catch {
      setError('Failed to load companies')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStoragePaths = async () => {
    try {
      // First get all integrations to find active Paperless integration
      const integrations = await api.get<IntegrationConfig[]>('/integrations?integration_type=paperless')
      const activeConfig = integrations.find(i => i.is_active)
      if (activeConfig) {
        const paths = await api.get<StoragePath[]>(`/integrations/${activeConfig.id}/storage-paths`)
        setStoragePaths(paths)
      }
    } catch {
      // Silently fail - storage paths are optional
    }
  }

  useEffect(() => {
    setBreadcrumb([{ label: 'Companies' }])
  }, [setBreadcrumb])

  useEffect(() => {
    fetchCompanies()
    fetchStoragePaths()
  }, [])

  const openModal = () => {
    reset({
      type: 'employer',
      name: '',
      expense_recipient_email: '',
      expense_recipient_name: '',
      paperless_storage_path_id: '',
    })
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    reset()
  }

  const onSubmit = async (data: CompanyForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        name: data.name,
        type: data.type,
        expense_recipient_email: data.expense_recipient_email || null,
        expense_recipient_name: data.expense_recipient_name || null,
        paperless_storage_path_id: data.paperless_storage_path_id
          ? parseInt(data.paperless_storage_path_id, 10)
          : null,
      }
      await api.post('/companies', payload)
      await fetchCompanies()
      closeModal()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save company')
    } finally {
      setIsSaving(false)
    }
  }

  const deleteCompany = async (id: string) => {
    if (!confirm('Are you sure you want to delete this company?')) return
    try {
      await api.delete(`/companies/${id}`)
      await fetchCompanies()
    } catch {
      setError('Failed to delete company')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
        <Button onClick={() => openModal()}>
          <Plus className="h-4 w-4 mr-2" />
          Add Company
        </Button>
      </div>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <Card>
        <CardHeader>
          <CardTitle>All Companies</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : companies.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No companies yet. Add your first company to get started.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {companies.map((company) => (
                <div
                  key={company.id}
                  className="flex items-center justify-between py-4 cursor-pointer hover:bg-gray-50 -mx-4 px-4 rounded"
                  onClick={() => navigate(`/companies/${company.id}`)}
                >
                  <div>
                    <h3 className="font-medium text-gray-900">{company.name}</h3>
                    <p className="text-sm text-gray-500">
                      {company.expense_recipient_email || 'No recipient email'}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={company.type === 'employer' ? 'info' : 'default'}>
                      {company.type === 'employer' ? 'Employer' : 'Third Party'}
                    </Badge>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteCompany(company.id)
                        }}
                        className="p-1 text-gray-400 hover:text-red-600"
                        title="Delete company"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title="Add Company"
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
            <Button type="button" variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Create
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
