import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2, CheckCircle, XCircle } from 'lucide-react'
import { api } from '@/api/client'
import type { IntegrationConfig, IntegrationTypeInfo } from '@/types'
import { useAuth } from '@/stores/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { Alert } from '@/components/ui/Alert'

const integrationSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  integration_type: z.string().min(1, 'Type is required'),
  url: z.string().url('Invalid URL'),
  token: z.string().min(1, 'Token is required'),
  custom_field_name: z.string().optional(),
})

type IntegrationForm = z.infer<typeof integrationSchema>

export function Settings() {
  const { user } = useAuth()
  const [integrations, setIntegrations] = useState<IntegrationConfig[]>([])
  const [types, setTypes] = useState<IntegrationTypeInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<IntegrationForm>({
    resolver: zodResolver(integrationSchema),
    defaultValues: {
      integration_type: 'paperless',
    },
  })

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
  }, [])

  const onSubmit = async (data: IntegrationForm) => {
    setIsSaving(true)
    setError(null)
    try {
      await api.post('/integrations', {
        name: data.name,
        integration_type: data.integration_type,
        config: {
          url: data.url,
          token: data.token,
          custom_field_name: data.custom_field_name || 'Trip',
        },
      })
      await fetchData()
      setIsModalOpen(false)
      reset()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create integration')
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
        onClose={() => {
          setIsModalOpen(false)
          reset()
        }}
        title="Add Integration"
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Name"
            {...register('name')}
            error={errors.name?.message}
            description="A friendly name for this integration"
          />
          <Select
            label="Type"
            options={typeOptions}
            {...register('integration_type')}
            error={errors.integration_type?.message}
          />
          <Input
            label="URL"
            {...register('url')}
            error={errors.url?.message}
            description="Base URL of the service (e.g., https://paperless.example.com)"
          />
          <Input
            label="API Token"
            type="password"
            {...register('token')}
            error={errors.token?.message}
          />
          <Input
            label="Custom Field Name"
            {...register('custom_field_name')}
            error={errors.custom_field_name?.message}
            description="Name of the custom field for event tagging (default: Trip)"
          />
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false)
                reset()
              }}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isSaving}>
              Add Integration
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
