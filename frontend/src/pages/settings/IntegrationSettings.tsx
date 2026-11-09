// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { api, errorMessage } from '@/api/client'
import {
  ImmichFields,
  LlmFields,
  PaperlessFields,
  SmtpFields,
  UnsplashFields,
} from '@/components/settings/IntegrationFields'
import { IntegrationList, type TestResult } from '@/components/settings/IntegrationList'
import {
  buildConfig,
  buildIntegrationSchema,
  fillIntegrationForm,
  type IntegrationConfigDetail,
  type IntegrationForm,
} from '@/components/settings/integrationForm'
import { TestEmailModal } from '@/components/settings/TestEmailModal'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { confirmAction } from '@/stores/confirm'
import type { IntegrationConfig, IntegrationTypeInfo } from '@/types'

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
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [llmModels, setLlmModels] = useState<string[]>([])
  const [isFetchingModels, setIsFetchingModels] = useState(false)
  // Kept out of the page-level error Alert, which renders behind the modal
  const [modelsError, setModelsError] = useState<string | null>(null)
  // Shown inside the edit modal when the stored config cannot be loaded (e.g. 403)
  const [configError, setConfigError] = useState<string | null>(null)
  // Secret fields with a stored value, from the server (the config value is masked)
  const [secretsSet, setSecretsSet] = useState<string[]>([])

  const integrationSchema = useMemo(() => buildIntegrationSchema(secretsSet), [secretsSet])

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
    } catch (e) {
      setError(errorMessage(e, 'Failed to load integrations'))
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
    setConfigError(null)
    setSecretsSet([])
    try {
      const detail = await api.get<IntegrationConfigDetail>(
        `/integrations/${integration.id}/config`,
      )
      fillIntegrationForm(setValue, detail)
      setSecretsSet(detail.secrets_set ?? [])
    } catch (e) {
      setConfigError(errorMessage(e, 'Failed to load integration configuration'))
    } finally {
      setIsLoadingConfig(false)
    }
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingIntegration(null)
    setLlmModels([])
    setModelsError(null)
    setConfigError(null)
    setSecretsSet([])
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
      setModelsError(errorMessage(e, 'Failed to fetch models'))
    } finally {
      setIsFetchingModels(false)
    }
  }

  const onSubmit = async (data: IntegrationForm) => {
    setIsSaving(true)
    setError(null)
    try {
      const config = buildConfig(data)
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
        errorMessage(
          e,
          editingIntegration ? 'Failed to update integration' : 'Failed to create integration',
        ),
      )
    } finally {
      setIsSaving(false)
    }
  }

  const deleteIntegration = async (id: string) => {
    if (
      !(await confirmAction({
        title: 'Delete integration',
        message: 'Are you sure you want to delete this integration?',
        confirmLabel: 'Delete',
      }))
    )
      return
    try {
      await api.delete(`/integrations/${id}`)
      await fetchData()
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete integration'))
    }
  }

  const testIntegration = async (id: string) => {
    setTestingId(id)
    try {
      const result = await api.post<TestResult>(`/integrations/${id}/test`)
      setTestResults((prev) => ({ ...prev, [id]: result }))
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, message: errorMessage(e, 'Test failed') },
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

  const closeTestEmailModal = () => {
    setIsTestEmailModalOpen(false)
    setTestEmailIntegrationId(null)
    setTestEmailAddress('')
  }

  const sendTestEmail = async () => {
    if (!testEmailIntegrationId || !testEmailAddress) return
    setSendingTestEmail(true)
    try {
      const result = await api.post<TestResult>(
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
          message: errorMessage(e, 'Failed to send test email'),
        },
      }))
    } finally {
      setSendingTestEmail(false)
    }
  }

  const typeOptions = types.map((t) => ({ value: t.type, label: t.name }))
  const fieldProps = { register, errors, secretsSet }

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
          <IntegrationList
            integrations={integrations}
            isLoading={isLoading}
            testResults={testResults}
            testingId={testingId}
            onTest={testIntegration}
            onSendTestEmail={openTestEmailModal}
            onEdit={openEditModal}
            onDelete={deleteIntegration}
          />
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
        ) : configError ? (
          <Alert variant="error">{configError}</Alert>
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

            {watchedType === 'paperless' && <PaperlessFields {...fieldProps} />}
            {watchedType === 'smtp' && <SmtpFields {...fieldProps} />}
            {watchedType === 'immich' && <ImmichFields {...fieldProps} />}
            {watchedType === 'unsplash' && <UnsplashFields {...fieldProps} />}
            {watchedType === 'llm' && (
              <LlmFields
                {...fieldProps}
                useBasicAuth={useBasicAuth}
                llmModels={llmModels}
                modelOptions={modelOptions}
                modelsError={modelsError}
                isFetchingModels={isFetchingModels}
                onFetchModels={fetchLlmModels}
              />
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

      <TestEmailModal
        isOpen={isTestEmailModalOpen}
        address={testEmailAddress}
        onAddressChange={setTestEmailAddress}
        result={testEmailIntegrationId ? testResults[testEmailIntegrationId] : undefined}
        isSending={sendingTestEmail}
        onSend={sendTestEmail}
        onClose={closeTestEmailModal}
      />
    </div>
  )
}
