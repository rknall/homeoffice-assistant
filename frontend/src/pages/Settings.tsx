import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, CheckCircle, XCircle, Mail, Pencil } from 'lucide-react'
import { api } from '@/api/client'
import type { IntegrationConfig, IntegrationTypeInfo, LocaleSettings } from '@/types'
import { useAuth } from '@/stores/auth'
import { useLocale } from '@/stores/locale'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'

interface IntegrationConfigDetail extends IntegrationConfig {
  config: Record<string, unknown>
}

// Paperless schema
const paperlessSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('paperless'),
  url: z.string().url('Invalid URL'),
  token: z.string().min(1, 'Token is required'),
  custom_field_name: z.string().optional(),
})

// SMTP schema
const smtpSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.literal('smtp'),
  host: z.string().min(1, 'Host is required'),
  port: z.string().min(1, 'Port is required'),
  username: z.string().optional(),
  password: z.string().optional(),
  from_email: z.string().email('Invalid email'),
  from_name: z.string().optional(),
  use_tls: z.boolean().optional(),
  use_ssl: z.boolean().optional(),
})

// Union schema for all integration types
const integrationSchema = z.discriminatedUnion('integration_type', [
  paperlessSchema,
  smtpSchema,
])

type IntegrationForm = z.infer<typeof integrationSchema>

const dateFormatOptions = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (2025-11-29)' },
  { value: 'DD.MM.YYYY', label: 'DD.MM.YYYY (29.11.2025)' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY (29/11/2025)' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY (11/29/2025)' },
]

const timeFormatOptions = [
  { value: '24h', label: '24-hour (14:30)' },
  { value: '12h', label: '12-hour (2:30 PM)' },
]

const timezoneOptions = [
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'Europe/London' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin' },
  { value: 'Europe/Paris', label: 'Europe/Paris' },
  { value: 'Europe/Amsterdam', label: 'Europe/Amsterdam' },
  { value: 'Europe/Vienna', label: 'Europe/Vienna' },
  { value: 'Europe/Zurich', label: 'Europe/Zurich' },
  { value: 'America/New_York', label: 'America/New York' },
  { value: 'America/Chicago', label: 'America/Chicago' },
  { value: 'America/Denver', label: 'America/Denver' },
  { value: 'America/Los_Angeles', label: 'America/Los Angeles' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney' },
]

export function Settings() {
  const { user } = useAuth()
  const { settings: localeSettings, fetchSettings: fetchLocaleSettings, updateSettings: updateLocaleSettings, isLoaded: localeLoaded } = useLocale()
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
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isSavingLocale, setIsSavingLocale] = useState(false)
  const [localeError, setLocaleError] = useState<string | null>(null)
  const [localeDateFormat, setLocaleDateFormat] = useState(localeSettings.date_format)
  const [localeTimeFormat, setLocaleTimeFormat] = useState(localeSettings.time_format)
  const [localeTimezone, setLocaleTimezone] = useState(localeSettings.timezone)

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<IntegrationForm>({
    resolver: zodResolver(integrationSchema),
    defaultValues: {
      integration_type: 'paperless',
    } as IntegrationForm,
  })

  const openEditModal = async (integration: IntegrationConfig) => {
    setEditingIntegration(integration)
    setIsLoadingConfig(true)
    setIsModalOpen(true)
    setError(null)
    try {
      const detail = await api.get<IntegrationConfigDetail>(`/integrations/${integration.id}/config`)
      setValue('name', detail.name)
      setValue('integration_type', detail.integration_type as 'paperless' | 'smtp')
      if (detail.integration_type === 'paperless') {
        setValue('url', detail.config.url as string || '')
        setValue('token', '')  // Leave empty, will preserve existing if not changed
        setValue('custom_field_name', detail.config.custom_field_name as string || '')
      } else if (detail.integration_type === 'smtp') {
        setValue('host', detail.config.host as string || '')
        setValue('port', String(detail.config.port || '587'))
        setValue('username', detail.config.username as string || '')
        setValue('password', '')  // Leave empty, will preserve existing if not changed
        setValue('from_email', detail.config.from_email as string || '')
        setValue('from_name', detail.config.from_name as string || '')
        setValue('use_tls', detail.config.use_tls as boolean ?? true)
        setValue('use_ssl', detail.config.use_ssl as boolean ?? false)
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
    reset()
  }

  const watchedType = watch('integration_type')

  const fetchData = async () => {
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
  }

  useEffect(() => {
    fetchData()
    if (!localeLoaded) {
      fetchLocaleSettings()
    }
  }, [])

  // Sync local state with locale settings when they load
  useEffect(() => {
    if (localeLoaded) {
      setLocaleDateFormat(localeSettings.date_format)
      setLocaleTimeFormat(localeSettings.time_format)
      setLocaleTimezone(localeSettings.timezone)
    }
  }, [localeLoaded, localeSettings])

  const saveLocaleSettings = async () => {
    setIsSavingLocale(true)
    setLocaleError(null)
    try {
      await updateLocaleSettings({
        date_format: localeDateFormat,
        time_format: localeTimeFormat,
        timezone: localeTimezone,
      })
    } catch (e) {
      setLocaleError(e instanceof Error ? e.message : 'Failed to save locale settings')
    } finally {
      setIsSavingLocale(false)
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
      } else {
        throw new Error('Unknown integration type')
      }

      if (editingIntegration) {
        // Update existing integration
        await api.put(`/integrations/${editingIntegration.id}`, {
          name: data.name,
          config,
        })
      } else {
        // Create new integration
        await api.post('/integrations', {
          name: data.name,
          integration_type: data.integration_type,
          config,
        })
      }
      await fetchData()
      closeModal()
    } catch (e) {
      setError(e instanceof Error ? e.message : editingIntegration ? 'Failed to update integration' : 'Failed to create integration')
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
      const result = await api.post<{ success: boolean; message: string }>(`/integrations/${id}/test`)
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
        { to_email: testEmailAddress }
      )
      setTestResults((prev) => ({ ...prev, [testEmailIntegrationId]: result }))
      if (result.success) {
        setIsTestEmailModalOpen(false)
      }
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [testEmailIntegrationId]: { success: false, message: e instanceof Error ? e.message : 'Failed to send test email' },
      }))
    } finally {
      setSendingTestEmail(false)
    }
  }

  const typeOptions = types.map((t) => ({ value: t.type, label: t.name }))

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Username</p>
                <p className="mt-1">{user?.username}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Email</p>
                <p className="mt-1">{user?.email}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Role</p>
                <p className="mt-1 capitalize">{user?.role}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Admin</p>
                <p className="mt-1">{user?.is_admin ? 'Yes' : 'No'}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {user?.is_admin && (
          <Card>
            <CardHeader>
              <CardTitle>Regional Settings</CardTitle>
            </CardHeader>
            <CardContent>
              {localeError && <Alert variant="error" className="mb-4">{localeError}</Alert>}
              <div className="space-y-4">
                <Select
                  label="Date Format"
                  options={dateFormatOptions}
                  value={localeDateFormat}
                  onChange={(e) => setLocaleDateFormat(e.target.value as LocaleSettings['date_format'])}
                />
                <Select
                  label="Time Format"
                  options={timeFormatOptions}
                  value={localeTimeFormat}
                  onChange={(e) => setLocaleTimeFormat(e.target.value as LocaleSettings['time_format'])}
                />
                <Select
                  label="Timezone"
                  options={timezoneOptions}
                  value={localeTimezone}
                  onChange={(e) => setLocaleTimezone(e.target.value)}
                />
                <div className="flex justify-end pt-2">
                  <Button onClick={saveLocaleSettings} isLoading={isSavingLocale}>
                    Save Regional Settings
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {user?.is_admin && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Integrations</CardTitle>
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
                    <div
                      key={integration.id}
                      className="flex items-center justify-between py-4"
                    >
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
                          onClick={() => openEditModal(integration)}
                          className="p-1 text-gray-400 hover:text-blue-600"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
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
        )}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingIntegration ? 'Edit Integration' : 'Add Integration'}
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
          {editingIntegration ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <p className="text-gray-900 capitalize">{editingIntegration.integration_type}</p>
            </div>
          ) : (
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
                error={'custom_field_name' in errors ? errors.custom_field_name?.message : undefined}
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

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={closeModal}
            >
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
