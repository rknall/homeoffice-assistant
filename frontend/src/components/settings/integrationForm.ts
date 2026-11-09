// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { UseFormSetValue } from 'react-hook-form'
import { z } from 'zod'
import { emailSchema } from '@/lib/validation'
import type { IntegrationConfig } from '@/types'

export interface IntegrationConfigDetail extends IntegrationConfig {
  config: Record<string, unknown>
  /** Names of secret fields with a stored value (their config value is masked). */
  secrets_set: string[]
}

/** A secret string: required unless a value is already stored for it. */
function secretField(secretsSet: string[], field: string, message: string) {
  return secretsSet.includes(field) ? z.string() : z.string().min(1, message)
}

const paperlessSchema = (secretsSet: string[]) =>
  z.object({
    name: z.string().min(1, 'Name is required').max(100),
    integration_type: z.literal('paperless'),
    url: z.string().url('Invalid URL'),
    token: secretField(secretsSet, 'token', 'Token is required'),
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

const immichSchema = (secretsSet: string[]) =>
  z.object({
    name: z.string().min(1, 'Name is required').max(100),
    integration_type: z.literal('immich'),
    url: z.string().url('Invalid URL'),
    api_key: secretField(secretsSet, 'api_key', 'API key is required'),
    search_radius_km: z.string().optional(),
  })

const unsplashSchema = (secretsSet: string[]) =>
  z.object({
    name: z.string().min(1, 'Name is required').max(100),
    integration_type: z.literal('unsplash'),
    access_key: secretField(secretsSet, 'access_key', 'Access key is required'),
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

/**
 * Build the form schema. Secret fields that already have a stored value (`secretsSet`,
 * edit mode) may be left blank to keep it; otherwise they are required.
 */
export function buildIntegrationSchema(secretsSet: string[] = []) {
  return z.discriminatedUnion('integration_type', [
    paperlessSchema(secretsSet),
    smtpSchema,
    immichSchema(secretsSet),
    unsplashSchema(secretsSet),
    llmSchema,
  ])
}

export const integrationSchema = buildIntegrationSchema()

export type IntegrationForm = z.infer<typeof integrationSchema>

export type IntegrationFormType = IntegrationForm['integration_type']

/** Placeholder for a password field whose secret is already stored. */
export function storedPlaceholder(secretsSet: string[], field: string): string | undefined {
  return secretsSet.includes(field) ? 'Stored, leave blank to keep' : undefined
}

/** Build the API config payload from the validated form values. */
export function buildConfig(data: IntegrationForm): Record<string, unknown> {
  if (data.integration_type === 'paperless') {
    return {
      url: data.url,
      token: data.token,
      custom_field_name: data.custom_field_name || 'Trip',
    }
  }
  if (data.integration_type === 'smtp') {
    return {
      host: data.host,
      port: parseInt(data.port, 10),
      username: data.username || '',
      password: data.password || '',
      from_email: data.from_email,
      from_name: data.from_name || '',
      use_tls: data.use_tls ?? true,
      use_ssl: data.use_ssl ?? false,
    }
  }
  if (data.integration_type === 'immich') {
    return {
      url: data.url,
      api_key: data.api_key,
      search_radius_km: parseInt(data.search_radius_km || '50', 10),
    }
  }
  if (data.integration_type === 'unsplash') {
    return {
      access_key: data.access_key,
      secret_key: data.secret_key || '',
    }
  }
  if (data.integration_type === 'llm') {
    return {
      base_url: data.base_url,
      api_key: data.api_key || '',
      username: data.use_basic_auth ? data.username || '' : '',
      password: data.use_basic_auth ? data.password || '' : '',
      model: data.model,
    }
  }
  throw new Error('Unknown integration type')
}

/** Fill the form from a stored integration (secret fields are left blank). */
export function fillIntegrationForm(
  setValue: UseFormSetValue<IntegrationForm>,
  detail: IntegrationConfigDetail,
): void {
  const { config } = detail
  setValue('name', detail.name)
  setValue('integration_type', detail.integration_type as IntegrationFormType)
  if (detail.integration_type === 'paperless') {
    setValue('url', (config.url as string) || '')
    setValue('token', '')
    setValue('custom_field_name', (config.custom_field_name as string) || '')
  } else if (detail.integration_type === 'smtp') {
    setValue('host', (config.host as string) || '')
    setValue('port', String(config.port || '587'))
    setValue('username', (config.username as string) || '')
    setValue('password', '')
    setValue('from_email', (config.from_email as string) || '')
    setValue('from_name', (config.from_name as string) || '')
    setValue('use_tls', (config.use_tls as boolean) ?? true)
    setValue('use_ssl', (config.use_ssl as boolean) ?? false)
  } else if (detail.integration_type === 'immich') {
    setValue('url', (config.url as string) || '')
    setValue('api_key', '')
    setValue('search_radius_km', String(config.search_radius_km || '50'))
  } else if (detail.integration_type === 'unsplash') {
    setValue('access_key', '')
    setValue('secret_key', '')
  } else if (detail.integration_type === 'llm') {
    setValue('base_url', (config.base_url as string) || '')
    setValue('api_key', '')
    setValue('use_basic_auth', Boolean(config.username))
    setValue('username', (config.username as string) || '')
    setValue('password', '')
    setValue('model', (config.model as string) || '')
  }
}
