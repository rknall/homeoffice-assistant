// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CompanyFormModal } from '@/components/CompanyFormModal'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

describe('CompanyFormModal logo rejection', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('stays open and shows the server message, without saving twice', async () => {
    const saved = { id: 'c9', name: 'Acme', type: 'employer', contacts: [] }
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith('/logo')) return Promise.resolve(json({ detail: 'Logo too wide' }, 400))
      if (init?.method === 'POST') return Promise.resolve(json(saved, 201))
      return Promise.resolve(json([]))
    })
    vi.stubGlobal('fetch', fetchMock)
    const onClose = vi.fn()
    const onSuccess = vi.fn()
    const user = userEvent.setup()
    const { container } = render(
      <CompanyFormModal isOpen onClose={onClose} onSuccess={onSuccess} />,
    )

    await user.type(screen.getByLabelText('Company Name'), 'Acme')
    const input = container.ownerDocument.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, new File(['x'], 'logo.png', { type: 'image/png' }))
    await user.click(screen.getByRole('button', { name: 'Create' }))

    expect(await screen.findByText(/Logo too wide/)).toBeTruthy()
    expect(onClose).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.filter(([, i]) => i?.method === 'POST')).toHaveLength(3),
    )
    // company POST + two logo uploads; the company itself was created once
    const companyPosts = fetchMock.mock.calls.filter(
      ([u, i]) => i?.method === 'POST' && !String(u).endsWith('/logo'),
    )
    expect(companyPosts).toHaveLength(1)
  })
})
