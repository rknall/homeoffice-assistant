// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Setup } from '@/pages/Setup'
import { useAuth } from '@/stores/auth'

describe('Setup', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('redirects to /login without navigating during render', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    useAuth.setState({ isFirstRun: false })
    render(
      <MemoryRouter initialEntries={['/setup']}>
        <Routes>
          <Route path="/setup" element={<Setup />} />
          <Route path="/login" element={<div>login page</div>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('login page')).toBeTruthy()
    expect(errorSpy).not.toHaveBeenCalled()
  })
})
