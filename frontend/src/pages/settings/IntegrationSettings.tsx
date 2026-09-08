// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { CheckCircle, Mail, Pencil, Plus, Trash2, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api } from '@/api/client'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import { emailSchema } from '@/lib/validation'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { IntegrationConfig, IntegrationTypeInfo } from '@/types'

interface IntegrationConfigDetail extends IntegrationConfig {
  config: Record<string, unknown>
}

const paperlessSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('paperless'),
  url: z.string().url('Invalid URL'),
  token: z.string().min(1, 'Token is required'),
  custom_field_name: z.string().optional(),
})

const smtpSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('smtp'),
  host: z.string().min(1, 'Host is required'),
  port: z.string().min(1, 'Port is required'),
  username: z.string().optional(),
  password: z.string().optional(),
  from_email: emailSchema,
  from_name: z.string().optional(),
  use_tls: z.boolean().optional(),
  use_ssl: z.boolean().optional(),
})

const immichSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('immich'),
  url: z.string().url('Invalid URL'),
  api_key: z.string().min(1, 'API key is required'),
  search_radius_km: z.string().optional(),
})

const unsplashSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('unsplash'),
  access_key: z.string().min(1, 'Access key is required'),
  secret_key: z.string().optional(),
})

const llmSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('llm'),
  base_url: z.string().url('Invalid URL'),
  api_key: z.string().optional(),
  use_basic_auth: z.boolean().optional(),
  username: z.string().optional(),
  password: z.string().optional(),
  model: z.string().min(1, 'Model is required'),
})

const integrationSchema = z.discriminatedUnion('integration_type', [
  paperlessSchema,
  smtpSchema,
  immichSchema,
  unsplashSchema,
  llmSchema,
])

type IntegrationForm = z.infer<typeof integrationSchema>

export function IntegrationSettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([])
  const [types, setTypes] = useState<IntegrationTypeInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingIntegration, setEditingIntegration] = useState<IntegrationConfig | null>(null)
  const [isLoadingConfig, setIsLoadingConfig] = useState(false)
  const [isTestEmailModalOpen, setIsTestEmailModalOpen] = useState(false)
  const [testEmailIntegrationId, setTestEmailIntegrationId] = useState<string | null>(null)
  const [testEmailAddress, setTestEmailAddress] = useState('')
  const [testingId, setTestingId] = useState<string | null>(null)
  const [sendingTestEmail, setSendingTestEmail] = useState(false)
  const [testResults, setTestResults] = useState<
    Record<string, { success: boolean; message: string }>
  >({})
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [llmModels, setLlmModels] = useState<string[]>([])
  const [isFetchingModels, setIsFetchingModels] = useState(false)
  // Kept out of the page-level error Alert, which renders behind the modal
  const [modelsError, setModelsError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<IntegrationForm>({
    resolver: zodResolver(integrationSchema),
    mode: 'onBlur',
    defaultValues: {
      integration_type: 'paperless',
    } as IntegrationForm,
  })

  const watchedType = watch('integration_type')
  const useBasicAuth = watch('use_basic_auth')
  const currentModel = watch('model')
  // Keep the saved model selectable even if the endpoint no longer lists it
  const modelOptions = [...new Set([...llmModels, currentModel].filter(Boolean))]
    .sort()
    .map((model) => ({ value: model as string, label: model as string }))

  // Prefill sensible defaults when creating a new LLM integration
  useEffect(() => {
    if (watchedType === 'llm' && !editingIntegration) {
      setValue('base_url', 'https://api.openai.com/v1')
      setValue('model', 'gpt-4o-mini')
    }
  }, [watchedType, editingIntegration, setValue])

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Integrations' }])
  }, [setBreadcrumb])

  const fetchData = useCallback(async () => {
    try {
      const [integrationsData, typesData] = await Promise.all([
        api.get<IntegrationConfig[]>('/integrations'),
        api.get<IntegrationTypeInfo[]>('/integrations/types'),
      ])
      setIntegrations(integrationsData)
      setTypes(typesData)
    } catch {
      setError('Failed to load integrations')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const openEditModal = async (integration: IntegrationConfig) => {
    setEditingIntegration(integration)
    setIsLoadingConfig(true)
    setIsModalOpen(true)
    setError(null)
    try {
      const detail = await api.get<IntegrationConfigDetail>(
        `/integrations/${integration.id}/config`,
      )
      setValue('name', detail.name)
      setValue(
        'integration_type',
        detail.integration_type as 'paperless' | 'smtp' | 'immich' | 'unsplash' | 'llm',
      )
      if (detail.integration_type === 'paperless') {
        setValue('url', (detail.config.url as string) || '')
        setValue('token', '')
        setValue('custom_field_name', (detail.config.custom_field_name as string) || '')
      } else if (detail.integration_type === 'smtp') {
        setValue('host', (detail.config.host as string) || '')
        setValue('port', String(detail.config.port || '587'))
        setValue('username', (detail.config.username as string) || '')
        setValue('password', '')
        setValue('from_email', (detail.config.from_email as string) || '')
        setValue('from_name', (detail.config.from_name as string) || '')
        setValue('use_tls', (detail.config.use_tls as boolean) ?? true)
        setValue('use_ssl', (detail.config.use_ssl as boolean) ?? false)
      } else if (detail.integration_type === 'immich') {
        setValue('url', (detail.config.url as string) || '')
        setValue('api_key', '')
        setValue('search_radius_km', String(detail.config.search_radius_km || '50'))
      } else if (detail.integration_type === 'unsplash') {
        setValue('access_key', '')
        setValue('secret_key', '')
      } else if (detail.integration_type === 'llm') {
        setValue('base_url', (detail.config.base_url as string) || '')
        setValue('api_key', '')
        setValue('use_basic_auth', Boolean(detail.config.username))
        setValue('username', (detail.config.username as string) || '')
        setValue('password', '')
        setValue('model', (detail.config.model as string) || '')
      }
    } catch {
      setError('Failed to load integration configuration')
    } finally {
      setIsLoadingConfig(false)
    }
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingIntegration(null)
    setLlmModels([])
    setModelsError(null)
    reset()
  }

  const fetchLlmModels = async () => {
    const values = getValues()
    if (values.integration_type !== 'llm') return
    setIsFetchingModels(true)
    setModelsError(null)
    try {
      const models = await api.post<string[]>('/integrations/llm/models', {
        base_url: values.base_url,
        api_key: values.api_key || '',
        username: values.use_basic_auth ? values.username || '' : '',
        password: values.use_basic_auth ? values.password || '' : '',
        config_id: editingIntegration?.id ?? null,
      })
      setLlmModels(models)
      if (models.length === 0) setModelsError('The endpoint returned no models')
    } catch (e) {
      setLlmModels([])
      setModelsError(e instanceof Error ? e.message : 'Failed to fetch models')
    } finally {
      setIsFetchingModels(false)
    }
  }

  const onSubmit = async (data: IntegrationForm) => {
    setIsSaving(true)
    setError(null)
    try {
      let config: Record<string, unknown>
      if (data.integration_type === 'paperless') {
        config = {
          url: data.url,
          token: data.token,
          custom_field_name: data.custom_field_name || 'Trip',
        }
      } else if (data.integration_type === 'smtp') {
        config = {
          host: data.host,
          port: parseInt(data.port, 10),
          username: data.username || '',
          password: data.password || '',
          from_email: data.from_email,
          from_name: data.from_name || '',
          use_tls: data.use_tls ?? true,
          use_ssl: data.use_ssl ?? false,
        }
      } else if (data.integration_type === 'immich') {
        config = {
          url: data.url,
          api_key: data.api_key,
          search_radius_km: parseInt(data.search_radius_km || '50', 10),
        }
      } else if (data.integration_type === 'unsplash') {
        config = {
          access_key: data.access_key,
          secret_key: data.secret_key || '',
        }
      } else if (data.integration_type === 'llm') {
        config = {
          base_url: data.base_url,
          api_key: data.api_key || '',
          username: data.use_basic_auth ? data.username || '' : '',
          password: data.use_basic_auth ? data.password || '' : '',
          model: data.model,
        }
      } else {
        throw new Error('Unknown integration type')
      }

      if (editingIntegration) {
        await api.put(`/integrations/${editingIntegration.id}`, {
          name: data.name,
          config,
        })
      } else {
        await api.post('/integrations', {
          name: data.name,
          integration_type: data.integration_type,
          config,
        })
      }
      await fetchData()
      closeModal()
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : editingIntegration
            ? 'Failed to update integration'
            : 'Failed to create integration',
      )
    } finally {
      setIsSaving(false)
    }
  }

  const deleteIntegration = async (id: string) => {
    if (!confirm('Are you sure you want to delete this integration?')) return
    try {
      await api.delete(`/integrations/${id}`)
      await fetchData()
    } catch {
      setError('Failed to delete integration')
    }
  }

  const testIntegration = async (id: string) => {
    setTestingId(id)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/integrations/${id}/test`,
      )
      setTestResults((prev) => ({ ...prev, [id]: result }))
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, message: e instanceof Error ? e.message : 'Test failed' },
      }))
    } finally {
      setTestingId(null)
    }
  }

  const openTestEmailModal = (id: string) => {
    setTestEmailIntegrationId(id)
    setTestEmailAddress('')
    setIsTestEmailModalOpen(true)
  }

  const sendTestEmail = async () => {
    if (!testEmailIntegrationId || !testEmailAddress) return
    setSendingTestEmail(true)
    try {
      const result = await api.post<{ success: boolean; message: string }>(
        `/integrations/${testEmailIntegrationId}/test-email`,
        { to_email: testEmailAddress },
      )
      setTestResults((prev) => ({ ...prev, [testEmailIntegrationId]: result }))
      if (result.success) {
        setIsTestEmailModalOpen(false)
      }
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [testEmailIntegrationId]: {
          success: false,
          message: e instanceof Error ? e.message : 'Failed to send test email',
        },
      }))
    } finally {
      setSendingTestEmail(false)
    }
  }

  const typeOptions = types.map((t) => ({ value: t.type, label: t.name }))

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Integrations</h1>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Connected Services</CardTitle>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Integration
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : integrations.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No integrations configured. Add your first integration to connect external services.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {integrations.map((integration) => (
                <div key={integration.id} className="flex items-center justify-between py-4">
                  <div>
                    <h3 className="font-medium text-gray-900">{integration.name}</h3>
                    <p className="text-sm text-gray-500 capitalize">
                      {integration.integration_type}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    {testResults[integration.id] && (
                      <div className="flex items-center gap-1">
                        {testResults[integration.id].success ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-sm text-gray-500">
                          {testResults[integration.id].message}
                        </span>
                      </div>
                    )}
                    <Badge variant={integration.is_active ? 'success' : 'default'}>
                      {integration.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => testIntegration(integration.id)}
                      isLoading={testingId === integration.id}
                    >
                      Test
                    </Button>
                    {integration.integration_type === 'smtp' && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => openTestEmailModal(integration.id)}
                      >
                        <Mail className="h-4 w-4 mr-1" />
                        Send Test
                      </Button>
                    )}
                    <button
                      type="button"
                      onClick={() => openEditModal(integration)}
                      className="p-1 text-gray-400 hover:text-blue-600"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteIntegration(integration.id)}
                      className="p-1 text-gray-400 hover:text-red-600"
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

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={
          editingIntegration
            ? `Edit Integration: ${
                types.find((t) => t.type === editingIntegration.integration_type)?.name ??
                editingIntegration.integration_type
              }`
            : 'Add Integration'
        }
        size="lg"
      >
        {isLoadingConfig ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Name"
              {...register('name')}
              error={errors.name?.message}
              description="A friendly name for this integration"
            />
            {!editingIntegration && (
              <Select
                label="Type"
                options={typeOptions}
                {...register('integration_type')}
                error={errors.integration_type?.message}
              />
            )}

            {watchedType === 'paperless' && (
              <>
                <Input
                  label="URL"
                  {...register('url')}
                  error={'url' in errors ? errors.url?.message : undefined}
                  description="Base URL of the service (e.g., https://paperless.example.com)"
                />
                <Input
                  label="API Token"
                  type="password"
                  {...register('token')}
                  error={'token' in errors ? errors.token?.message : undefined}
                />
                <Input
                  label="Custom Field Name"
                  {...register('custom_field_name')}
                  error={
                    'custom_field_name' in errors ? errors.custom_field_name?.message : undefined
                  }
                  description="Name of the custom field for event tagging (default: Trip)"
                />
              </>
            )}

            {watchedType === 'smtp' && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="SMTP Host"
                    {...register('host')}
                    error={'host' in errors ? errors.host?.message : undefined}
                  />
                  <Input
                    label="Port"
                    type="number"
                    {...register('port')}
                    error={'port' in errors ? errors.port?.message : undefined}
                    defaultValue="587"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Username (optional)"
                    {...register('username')}
                    error={'username' in errors ? errors.username?.message : undefined}
                  />
                  <Input
                    label="Password (optional)"
                    type="password"
                    {...register('password')}
                    error={'password' in errors ? errors.password?.message : undefined}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="From Email"
                    type="email"
                    {...register('from_email')}
                    error={'from_email' in errors ? errors.from_email?.message : undefined}
                  />
                  <Input
                    label="From Name (optional)"
                    {...register('from_name')}
                    error={'from_name' in errors ? errors.from_name?.message : undefined}
                  />
                </div>
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      {...register('use_tls')}
                      defaultChecked
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Use TLS</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      {...register('use_ssl')}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm text-gray-700">Use SSL</span>
                  </label>
                </div>
              </>
            )}

            {watchedType === 'immich' && (
              <>
                <Input
                  label="URL"
                  {...register('url')}
                  error={'url' in errors ? errors.url?.message : undefined}
                  description="Base URL of your Immich server (e.g., https://immich.example.com)"
                />
                <Input
                  label="API Key"
                  type="password"
                  {...register('api_key')}
                  error={'api_key' in errors ? errors.api_key?.message : undefined}
                  description="Your Immich API key (found in Account Settings)"
                />
                <Input
                  label="Search Radius (km)"
                  type="number"
                  {...register('search_radius_km')}
                  error={
                    'search_radius_km' in errors ? errors.search_radius_km?.message : undefined
                  }
                  description="Maximum distance from event location to search for photos (default: 50km)"
                  defaultValue="50"
                />
              </>
            )}

            {watchedType === 'unsplash' && (
              <>
                <Input
                  label="Access Key"
                  type="password"
                  {...register('access_key')}
                  error={'access_key' in errors ? errors.access_key?.message : undefined}
                  description="Unsplash API Access Key (from unsplash.com/developers)"
                />
                <Input
                  label="Secret Key (optional)"
                  type="password"
                  {...register('secret_key')}
                  error={'secret_key' in errors ? errors.secret_key?.message : undefined}
                  description="Unsplash API Secret Key (only needed for OAuth flows)"
                />
              </>
            )}

            {watchedType === 'llm' && (
              <>
                <Input
                  label="Base URL"
                  {...register('base_url')}
                  error={'base_url' in errors ? errors.base_url?.message : undefined}
                  description="OpenAI-compatible API base URL, e.g. a LiteLLM proxy or https://api.openai.com/v1"
                />
                <Input
                  label="API Key"
                  type="password"
                  {...register('api_key')}
                  error={'api_key' in errors ? errors.api_key?.message : undefined}
                  description="Sent as a Bearer token, or as x-api-key with basic auth"
                />
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    {...register('use_basic_auth')}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">
                    Use basic authentication (API behind a gateway)
                  </span>
                </label>
                {useBasicAuth && (
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="Username"
                      {...register('username')}
                      error={'username' in errors ? errors.username?.message : undefined}
                    />
                    <Input
                      label="Password"
                      type="password"
                      {...register('password')}
                      error={'password' in errors ? errors.password?.message : undefined}
                    />
                  </div>
                )}
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    {llmModels.length > 0 ? (
                      <Select
                        label="Model"
                        options={modelOptions}
                        {...register('model')}
                        error={'model' in errors ? errors.model?.message : undefined}
                      />
                    ) : (
                      <Input
                        label="Model"
                        {...register('model')}
                        error={'model' in errors ? errors.model?.message : undefined}
                        description="Model name, e.g. gpt-4o-mini"
                      />
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    className="mt-6"
                    onClick={fetchLlmModels}
                    isLoading={isFetchingModels}
                  >
                    Fetch models
                  </Button>
                </div>
                {modelsError && <p className="-mt-2 text-sm text-red-600">{modelsError}</p>}
              </>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="secondary" onClick={closeModal}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isSaving}>
                {editingIntegration ? 'Save Changes' : 'Add Integration'}
              </Button>
            </div>
          </form>
        )}
      </Modal>

      <Modal
        isOpen={isTestEmailModalOpen}
        onClose={() => {
          setIsTestEmailModalOpen(false)
          setTestEmailIntegrationId(null)
          setTestEmailAddress('')
        }}
        title="Send Test Email"
      >
        <div className="space-y-4">
          <Input
            label="Recipient Email"
            type="email"
            value={testEmailAddress}
            onChange={(e) => setTestEmailAddress(e.target.value)}
            description="Enter the email address to receive the test email"
          />
          {testEmailIntegrationId && testResults[testEmailIntegrationId] && (
            <Alert variant={testResults[testEmailIntegrationId].success ? 'success' : 'error'}>
              {testResults[testEmailIntegrationId].message}
            </Alert>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsTestEmailModalOpen(false)
                setTestEmailIntegrationId(null)
                setTestEmailAddress('')
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={sendTestEmail}
              isLoading={sendingTestEmail}
              disabled={!testEmailAddress}
            >
              Send Test Email
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
