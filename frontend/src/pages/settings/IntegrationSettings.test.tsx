// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { IntegrationSettings } from '@/pages/settings/IntegrationSettings'

const integration = {
  id: 'i1',
  name: 'My LLM',
  integration_type: 'llm',
  is_active: true,
  created_at: '2025-01-01T00:00:00',
  updated_at: '2025-01-01T00:00:00',
}

function stubApi(configResponse: { status: number; body: unknown }) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const respond = (status: number, body: unknown) => ({
        ok: status < 300,
        status,
        json: async () => body,
      })
      if (url.endsWith('/integrations/i1/config')) {
        return respond(configResponse.status, configResponse.body)
      }
      if (url.endsWith('/integrations/types')) {
        return respond(200, [{ type: 'llm', name: 'LLM', description: 'd', config_schema: {} }])
      }
      return respond(200, [integration])
    }),
  )
}

async function openEdit() {
  render(
    <MemoryRouter>
      <IntegrationSettings />
    </MemoryRouter>,
  )
  const edit = await screen.findByLabelText('Edit integration')
  fireEvent.click(edit)
}

describe('IntegrationSettings LLM edit modal', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows the server 403 message instead of a blank form', async () => {
    stubApi({ status: 403, body: { detail: 'Missing permission integrations.read' } })
    await openEdit()
    expect(await screen.findByText('Missing permission integrations.read')).toBeTruthy()
    expect(screen.queryByText('API Key')).toBeNull()
  })

  it('hints that an API key is stored without revealing it', async () => {
    stubApi({
      status: 200,
      body: {
        ...integration,
        config: { base_url: 'https://x/v1', api_key: '', model: 'm' },
        secrets_set: ['api_key'],
      },
    })
    await openEdit()
    const input = await waitFor(() => screen.getByPlaceholderText('Stored, leave blank to keep'))
    expect((input as HTMLInputElement).value).toBe('')
  })

  it('shows no hint when no API key is stored', async () => {
    stubApi({
      status: 200,
      body: {
        ...integration,
        config: { base_url: 'https://x/v1', api_key: '', model: 'm' },
        secrets_set: [],
      },
    })
    await openEdit()
    await screen.findByText('API Key')
    expect(screen.queryByPlaceholderText('Stored, leave blank to keep')).toBeNull()
  })
})

interface SecretCase {
  type: string
  label: string
  secret: string
  config: Record<string, unknown>
  required: string
  fill: Record<string, string>
}

const secretCases: SecretCase[] = [
  {
    type: 'paperless',
    label: 'API Token',
    secret: 'token',
    config: { url: 'https://p.example.com', token: '', custom_field_name: 'Trip' },
    required: 'Token is required',
    fill: { URL: 'https://p.example.com' },
  },
  {
    type: 'immich',
    label: 'API Key',
    secret: 'api_key',
    config: { url: 'https://i.example.com', api_key: '', search_radius_km: 50 },
    required: 'API key is required',
    fill: { URL: 'https://i.example.com' },
  },
  {
    type: 'unsplash',
    label: 'Access Key',
    secret: 'access_key',
    config: { access_key: '', secret_key: '' },
    required: 'Access key is required',
    fill: {},
  },
]

function stubSecretApi(c: SecretCase, secretsSet: string[]) {
  const item = { ...integration, id: 'i1', name: 'Stored one', integration_type: c.type }
  const puts: unknown[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
      const respond = (body: unknown) => ({ ok: true, status: 200, json: async () => body })
      if (init?.method === 'PUT') {
        puts.push(JSON.parse(init.body ?? '{}'))
        return respond(item)
      }
      if (url.endsWith('/integrations/i1/config')) {
        return respond({ ...item, config: c.config, secrets_set: secretsSet })
      }
      if (url.endsWith('/integrations/types')) {
        return respond([{ type: c.type, name: c.type, description: 'd', config_schema: {} }])
      }
      return respond([item])
    }),
  )
  return puts
}

describe.each(secretCases)('IntegrationSettings stored $type secret', (c) => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows the stored placeholder and saves with the field blank', async () => {
    const puts = stubSecretApi(c, [c.secret])
    await openEdit()
    const input = await waitFor(() => screen.getByPlaceholderText('Stored, leave blank to keep'))
    expect((input as HTMLInputElement).value).toBe('')
    fireEvent.click(screen.getByText('Save Changes'))
    await waitFor(() => expect(puts.length).toBe(1))
    expect(screen.queryByText(c.required)).toBeNull()
    expect((puts[0] as { config: Record<string, unknown> }).config[c.secret]).toBe('')
  })

  it('still requires the secret when nothing is stored', async () => {
    const puts = stubSecretApi(c, [])
    await openEdit()
    await screen.findByText(c.label)
    expect(screen.queryByPlaceholderText('Stored, leave blank to keep')).toBeNull()
    fireEvent.click(screen.getByText('Save Changes'))
    expect(await screen.findByText(c.required)).toBeTruthy()
    expect(puts.length).toBe(0)
  })
})

describe('IntegrationSettings create', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('requires the Paperless token when creating', async () => {
    stubApi({ status: 200, body: {} })
    render(
      <MemoryRouter>
        <IntegrationSettings />
      </MemoryRouter>,
    )
    fireEvent.click((await screen.findAllByText('Add Integration'))[0])
    fireEvent.change(await screen.findByLabelText('URL'), {
      target: { value: 'https://p.example.com' },
    })
    fireEvent.click(screen.getAllByText('Add Integration').at(-1) as HTMLElement)
    expect(await screen.findByText('Token is required')).toBeTruthy()
  })
})
