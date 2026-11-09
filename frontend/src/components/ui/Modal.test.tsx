// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Modal } from '@/components/ui/Modal'

describe('Modal Escape', () => {
  afterEach(cleanup)

  it('closes on Escape while open', async () => {
    const onClose = vi.fn()
    render(
      <Modal isOpen onClose={onClose} title="T">
        body
      </Modal>,
    )
    await userEvent.setup().keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('ignores Escape when closed', async () => {
    const onClose = vi.fn()
    render(
      <Modal isOpen={false} onClose={onClose}>
        body
      </Modal>,
    )
    await userEvent.setup().keyboard('{Escape}')
    expect(onClose).not.toHaveBeenCalled()
  })

  it('does not close when a nested dialog handled Escape', async () => {
    const onClose = vi.fn()
    render(
      <Modal isOpen onClose={onClose} title="T">
        <button
          type="button"
          onKeyDown={(e) => {
            if (e.key === 'Escape') e.preventDefault()
          }}
        >
          inner
        </button>
      </Modal>,
    )
    await userEvent.setup().click(screen.getByText('inner'))
    await userEvent.setup().keyboard('{Escape}')
    expect(onClose).not.toHaveBeenCalled()
  })
})
