// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { Upload, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, getCompanyLogoUrl, uploadCompanyLogo } from '@/api/client'
import { CountryAutocomplete } from '@/components/CountryAutocomplete'
import { Button } from '@/components/ui/Button'
import { CurrencySelect } from '@/components/ui/CurrencySelect'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import type { Company, IntegrationConfig, StoragePath } from '@/types'

const companySchema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  type: z.enum(['employer', 'third_party']),
  webpage: z.string().url('Invalid URL').max(500).optional().or(z.literal('')),
  address: z.string().max(1000).optional(),
  country: z.string().max(100).optional(),
  paperless_storage_path_id: z.string().optional(),
  base_currency: z.string().length(3, 'Currency must be 3 characters').optional(),
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

export function CompanyFormModal({ isOpen, onClose, onSuccess, company }: CompanyFormModalProps) {
  const isEditMode = !!company
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [storagePaths, setStoragePaths] = useState<StoragePath[]>([])
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [isUploadingLogo, setIsUploadingLogo] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CompanyFormData>({
    resolver: zodResolver(companySchema),
    mode: 'onBlur',
  })

  const currentCountry = watch('country')
  const currentBaseCurrency = watch('base_currency')

  // Fetch storage paths for Paperless integration
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
      // Silently fail - storage paths are optional
    }
  }, [])

  // Detect browser country for prefilling
  const detectBrowserCountry = useCallback((): string => {
    const locale = navigator.language || 'en-US'
    const parts = locale.split('-')
    if (parts.length === 2) {
      // Convert country code to name (basic mapping)
      const countryNames: Record<string, string> = {
        US: 'United States',
        GB: 'United Kingdom',
        DE: 'Germany',
        FR: 'France',
        AT: 'Austria',
        CH: 'Switzerland',
        IT: 'Italy',
        ES: 'Spain',
        NL: 'Netherlands',
        BE: 'Belgium',
        CA: 'Canada',
        AU: 'Australia',
      }
      return countryNames[parts[1]] || ''
    }
    return ''
  }, [])

  // Reset form when modal opens/closes or company changes
  useEffect(() => {
    if (isOpen) {
      fetchStoragePaths()
      setLogoFile(null)

      if (company) {
        reset({
          name: company.name,
          type: company.type,
          webpage: company.webpage || '',
          address: company.address || '',
          country: company.country || '',
          paperless_storage_path_id: company.paperless_storage_path_id?.toString() || '',
          base_currency: company.base_currency || 'EUR',
        })
        setLogoPreview(company.logo_path ? getCompanyLogoUrl(company.id) : null)
      } else {
        const detectedCountry = detectBrowserCountry()
        reset({
          name: '',
          type: 'employer',
          webpage: '',
          address: '',
          country: detectedCountry,
          paperless_storage_path_id: '',
          base_currency: 'EUR',
        })
        setLogoPreview(null)
      }
      setError(null)
    }
  }, [isOpen, company, reset, fetchStoragePaths, detectBrowserCountry])

  const handleClose = () => {
    onClose()
  }

  const handleLogoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml', 'image/webp']
      if (!validTypes.includes(file.type)) {
        setError('Invalid file type. Please select PNG, JPG, GIF, SVG, or WebP.')
        return
      }
      // Validate file size (5MB)
      if (file.size > 5 * 1024 * 1024) {
        setError('File too large. Maximum size is 5MB.')
        return
      }
      setLogoFile(file)
      setLogoPreview(URL.createObjectURL(file))
      setError(null)
    }
  }

  const removeLogo = async () => {
    if (isEditMode && company?.logo_path) {
      try {
        await api.delete(`/companies/${company.id}/logo`)
      } catch {
        setError('Failed to remove logo')
        return
      }
    }
    setLogoFile(null)
    setLogoPreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const onSubmit = async (data: CompanyFormData) => {
    setIsSaving(true)
    setError(null)

    try {
      const payload = {
        name: data.name,
        type: data.type,
        webpage: data.webpage || null,
        address: data.address || null,
        country: data.country || null,
        paperless_storage_path_id: data.paperless_storage_path_id
          ? parseInt(data.paperless_storage_path_id, 10)
          : null,
        base_currency: data.base_currency || 'EUR',
      }

      let savedCompany: Company

      if (isEditMode && company) {
        savedCompany = await api.put<Company>(`/companies/${company.id}`, payload)
      } else {
        savedCompany = await api.post<Company>('/companies', payload)
      }

      // Upload logo if a new file was selected
      if (logoFile) {
        setIsUploadingLogo(true)
        try {
          await uploadCompanyLogo(savedCompany.id, logoFile)
        } catch {
          // Don't fail the whole operation, just warn
          console.error('Failed to upload logo')
        }
        setIsUploadingLogo(false)
      }

      onSuccess(savedCompany)
      handleClose()
    } catch (e) {
      setError(
        e instanceof Error ? e.message : `Failed to ${isEditMode ? 'update' : 'create'} company`,
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditMode ? 'Edit Company' : 'Add Company'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {error && <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{error}</div>}

        {/* Logo Upload */}
        <div>
          <span className="block text-sm font-medium text-gray-700 mb-2">Company Logo</span>
          <div className="flex items-center gap-4">
            {logoPreview ? (
              <div className="relative">
                <img
                  src={logoPreview}
                  alt="Logo preview"
                  className="h-20 w-20 object-contain rounded-lg border border-gray-200"
                />
                <button
                  type="button"
                  onClick={removeLogo}
                  className="absolute -top-2 -right-2 p-1 bg-red-100 rounded-full text-red-600 hover:bg-red-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="h-20 w-20 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center cursor-pointer hover:border-gray-400"
              >
                <Upload className="h-6 w-6 text-gray-400" />
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/svg+xml,image/webp"
              onChange={handleLogoSelect}
              className="hidden"
            />
            <div className="text-sm text-gray-500">
              <p>Click to upload logo</p>
              <p>PNG, JPG, GIF, SVG, WebP (max 5MB)</p>
            </div>
          </div>
        </div>

        <Input label="Company Name" {...register('name')} error={errors.name?.message} />

        <Select
          label="Type"
          options={typeOptions}
          {...register('type')}
          error={errors.type?.message}
        />

        <Input
          label="Website"
          type="url"
          placeholder="https://example.com"
          {...register('webpage')}
          error={errors.webpage?.message}
        />

        <div>
          <label htmlFor="company-address" className="block text-sm font-medium text-gray-700 mb-1">
            Address
          </label>
          <textarea
            id="company-address"
            {...register('address')}
            rows={3}
            placeholder="Street, City, Postal Code..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <CountryAutocomplete
          label="Country"
          value={currentCountry || ''}
          onChange={(value) => setValue('country', value)}
          error={errors.country?.message}
        />

        <CurrencySelect
          label="Base Currency"
          defaultValue={currentBaseCurrency || 'EUR'}
          {...register('base_currency')}
          error={errors.base_currency?.message}
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
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving || isUploadingLogo}>
            {isEditMode ? 'Save Changes' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
