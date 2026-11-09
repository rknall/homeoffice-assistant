// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { FieldErrors, UseFormRegister } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { type IntegrationForm, storedPlaceholder } from './integrationForm'

interface FieldsProps {
  register: UseFormRegister<IntegrationForm>
  errors: FieldErrors<IntegrationForm>
  secretsSet: string[]
}

export function PaperlessFields({ register, errors, secretsSet }: FieldsProps) {
  return (
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
        placeholder={storedPlaceholder(secretsSet, 'token')}
        error={'token' in errors ? errors.token?.message : undefined}
      />
      <Input
        label="Custom Field Name"
        {...register('custom_field_name')}
        error={'custom_field_name' in errors ? errors.custom_field_name?.message : undefined}
        description="Name of the custom field for event tagging (default: Trip)"
      />
    </>
  )
}

export function SmtpFields({ register, errors, secretsSet }: FieldsProps) {
  return (
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
          placeholder={storedPlaceholder(secretsSet, 'password')}
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
          <input type="checkbox" {...register('use_ssl')} className="rounded border-gray-300" />
          <span className="text-sm text-gray-700">Use SSL</span>
        </label>
      </div>
    </>
  )
}

export function ImmichFields({ register, errors, secretsSet }: FieldsProps) {
  return (
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
        placeholder={storedPlaceholder(secretsSet, 'api_key')}
        error={'api_key' in errors ? errors.api_key?.message : undefined}
        description="Your Immich API key (found in Account Settings)"
      />
      <Input
        label="Search Radius (km)"
        type="number"
        {...register('search_radius_km')}
        error={'search_radius_km' in errors ? errors.search_radius_km?.message : undefined}
        description="Maximum distance from event location to search for photos (default: 50km)"
        defaultValue="50"
      />
    </>
  )
}

export function UnsplashFields({ register, errors, secretsSet }: FieldsProps) {
  return (
    <>
      <Input
        label="Access Key"
        type="password"
        {...register('access_key')}
        placeholder={storedPlaceholder(secretsSet, 'access_key')}
        error={'access_key' in errors ? errors.access_key?.message : undefined}
        description="Unsplash API Access Key (from unsplash.com/developers)"
      />
      <Input
        label="Secret Key (optional)"
        type="password"
        {...register('secret_key')}
        placeholder={storedPlaceholder(secretsSet, 'secret_key')}
        error={'secret_key' in errors ? errors.secret_key?.message : undefined}
        description="Unsplash API Secret Key (only needed for OAuth flows)"
      />
    </>
  )
}

interface LlmFieldsProps extends FieldsProps {
  useBasicAuth: boolean | undefined
  llmModels: string[]
  modelOptions: { value: string; label: string }[]
  modelsError: string | null
  isFetchingModels: boolean
  onFetchModels: () => void
}

export function LlmFields({
  register,
  errors,
  secretsSet,
  useBasicAuth,
  llmModels,
  modelOptions,
  modelsError,
  isFetchingModels,
  onFetchModels,
}: LlmFieldsProps) {
  return (
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
        placeholder={storedPlaceholder(secretsSet, 'api_key')}
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
            placeholder={storedPlaceholder(secretsSet, 'password')}
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
          onClick={onFetchModels}
          isLoading={isFetchingModels}
        >
          Fetch models
        </Button>
      </div>
      {modelsError && <p className="-mt-2 text-sm text-red-600">{modelsError}</p>}
    </>
  )
}
