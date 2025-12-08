// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '@/api/client'
import type { Company, IntegrationConfig, StoragePath } from '@/types'
import { optionalEmailSchema } from '@/lib/validation'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'

const companySchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  type: z.enum(['employer', 'third_party']),
  expense_recipient_email: optionalEmailSchema,
  expense_recipient_name: z.string().max(200).optional(),
  paperless_storage_path_id: z.string().optional(),
})

type CompanyFormData = z.infer<typeof companySchema>

const typeOptions = [
  { value: 'employer', label: 'Employer' },
  { value: 'third_party', label: 'Third Party' },
]

interface CompanyFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (company?: Company) => void
  company?: Company | null // If provided, it's edit mode; otherwise, create mode
}

export function CompanyFormModal({
  isOpen,
  onClose,
  onSuccess,
  company,
}: CompanyFormModalProps) {
  const isEditMode = !!company
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [storagePaths, setStoragePaths] = useState<StoragePath[]>([])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CompanyFormData>({
    resolver: zodResolver(companySchema),
    mode: 'onBlur',
  })

  // Fetch storage paths for Paperless integration
  const fetchStoragePaths = async () => {
    try {
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

  // Reset form when modal opens/closes or company changes
  useEffect(() => {
    if (isOpen) {
      fetchStoragePaths()
      if (company) {
        reset({
          name: company.name,
          type: company.type,
          expense_recipient_email: company.expense_recipient_email || '',
          expense_recipient_name: company.expense_recipient_name || '',
          paperless_storage_path_id: company.paperless_storage_path_id?.toString() || '',
        })
      } else {
        reset({
          name: '',
          type: 'employer',
          expense_recipient_email: '',
          expense_recipient_name: '',
          paperless_storage_path_id: '',
        })
      }
      setError(null)
    }
  }, [isOpen, company, reset])

  const handleClose = () => {
    onClose()
  }

  const onSubmit = async (data: CompanyFormData) => {
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

      if (isEditMode && company) {
        await api.put(`/companies/${company.id}`, payload)
        onSuccess()
      } else {
        const newCompany = await api.post<Company>('/companies', payload)
        onSuccess(newCompany)
      }

      handleClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${isEditMode ? 'update' : 'create'} company`)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditMode ? 'Edit Company' : 'Add Company'}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}

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
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            {isEditMode ? 'Save Changes' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
