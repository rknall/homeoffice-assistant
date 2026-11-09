// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ConfirmDialogHost } from '@/components/ui/ConfirmDialog'
import { EventDetail } from '@/pages/EventDetail'

const event = {
  id: 'e1',
  name: 'Beta Site Visit',
  company_id: 'c1',
  company_name: 'Beta',
  start_date: '2026-11-18',
  end_date: '2026-11-20',
  status: 'upcoming',
  city: null,
  country: null,
}

const expense = {
  id: 'x1',
  date: '2026-11-18',
  amount: 12,
  currency: 'EUR',
  payment_type: 'cash',
  category: 'transport',
  description: 'Parking',
  status: 'pending',
  is_private: false,
  rejection_reason: null,
  paperless_doc_id: null,
}

const preview = { total: 12, currency: 'EUR', expense_count: 1, documents_available: 0 }

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), { status })
}

describe('EventDetail', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'DELETE') return Promise.resolve(jsonResponse(null, 204))
      if (url.endsWith('/events/e1')) return Promise.resolve(jsonResponse(event))
      if (url.endsWith('/events/e1/expenses')) return Promise.resolve(jsonResponse([expense]))
      if (url.endsWith('/expense-report/preview')) return Promise.resolve(jsonResponse(preview))
      return Promise.resolve(jsonResponse([]))
    })
    vi.stubGlobal('fetch', fetchMock)
    render(
      <MemoryRouter initialEntries={['/events/e1']}>
        <Routes>
          <Route path="/events/:id" element={<EventDetail />} />
        </Routes>
        <ConfirmDialogHost />
      </MemoryRouter>,
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  const deleteCalls = () => fetchMock.mock.calls.filter(([, init]) => init?.method === 'DELETE')

  it('renders the header, summary and expense row', async () => {
    expect(await screen.findByText('Beta Site Visit')).toBeTruthy()
    expect(await screen.findByText('Parking')).toBeTruthy()
    expect(screen.getByText('Total Expenses')).toBeTruthy()
  })

  it('confirms before deleting an expense', async () => {
    const user = userEvent.setup()
    await user.click(await screen.findByTitle('Delete expense'))
    expect(await screen.findByText('Are you sure you want to delete this expense?')).toBeTruthy()
    expect(deleteCalls()).toHaveLength(0)
    await user.click(screen.getByRole('button', { name: 'Delete' }))
    await vi.waitFor(() => expect(deleteCalls()).toHaveLength(1))
  })

  it('shows the bulk bar after selecting an expense and opens the edit modal', async () => {
    const user = userEvent.setup()
    await user.click(await screen.findByLabelText('Select expense Parking'))
    expect(screen.getByText('1 expense selected')).toBeTruthy()
    await user.click(screen.getByTitle('Edit expense'))
    expect(await screen.findByText('Edit Expense')).toBeTruthy()
  })
})
