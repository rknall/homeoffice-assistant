// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { ConfirmDialogHost } from '@/components/ui/ConfirmDialog'
import { installHostApi } from '@/plugins/hostApi'
import { confirmAction, useConfirm } from '@/stores/confirm'

const base = { title: 'Delete company', message: 'Delete Acme?' }

function open(options: Partial<Parameters<typeof confirmAction>[0]> = {}) {
  render(<ConfirmDialogHost />)
  const result = confirmAction({ ...base, ...options })
  return result
}

describe('ConfirmDialog', () => {
  afterEach(() => {
    cleanup()
    useConfirm.setState({ request: null })
  })

  it('resolves true on confirm', async () => {
    const result = open()
    await userEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await result).toBe(true)
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })

  it('resolves false on Cancel', async () => {
    const result = open()
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
    expect(await result).toBe(false)
  })

  it('resolves false on Escape', async () => {
    const result = open()
    await screen.findByRole('alertdialog')
    await userEvent.keyboard('{Escape}')
    expect(await result).toBe(false)
  })

  it('resolves false on backdrop click', async () => {
    const result = open()
    await userEvent.click(await screen.findByTestId('confirm-backdrop'))
    expect(await result).toBe(false)
  })

  it('focuses Cancel for danger and shows the red button', async () => {
    open()
    const dialog = await screen.findByRole('alertdialog')
    expect(dialog.querySelector('button:focus')?.textContent).toBe('Cancel')
    expect(screen.getByRole('button', { name: 'Delete' }).className).toContain('bg-red-600')
  })

  it('focuses the confirm button for primary', async () => {
    open({ variant: 'primary' })
    const confirmButton = await screen.findByRole('button', { name: 'Confirm' })
    expect(document.activeElement).toBe(confirmButton)
    expect(confirmButton.className).toContain('bg-blue-600')
  })

  it('wraps Tab from the last button to the first and back with Shift+Tab', async () => {
    open()
    const cancel = await screen.findByRole('button', { name: 'Cancel' })
    const del = screen.getByRole('button', { name: 'Delete' })
    expect(document.activeElement).toBe(cancel)
    await userEvent.tab()
    expect(document.activeElement).toBe(del)
    await userEvent.tab()
    expect(document.activeElement).toBe(cancel)
    await userEvent.tab({ shift: true })
    expect(document.activeElement).toBe(del)
  })

  it('names the alertdialog by its title', async () => {
    open()
    expect(await screen.findByRole('alertdialog', { name: 'Delete company' })).toBeTruthy()
  })

  it('resolves the first request with false when a second opens', async () => {
    const first = open()
    await screen.findByRole('alertdialog')
    const second = confirmAction({ title: 'Other', message: 'Other?' })
    expect(await first).toBe(false)
    await userEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(await second).toBe(true)
  })

  it('Enter on the focused confirm button (primary) resolves true', async () => {
    const result = open({ variant: 'primary' })
    await screen.findByRole('alertdialog')
    await userEvent.keyboard('{Enter}')
    expect(await result).toBe(true)
  })

  it('Enter on the focused Cancel (danger) resolves false', async () => {
    const result = open()
    await screen.findByRole('alertdialog')
    await userEvent.keyboard('{Enter}')
    expect(await result).toBe(false)
  })

  it('returns focus to the previously focused element', async () => {
    const trigger = document.createElement('button')
    document.body.appendChild(trigger)
    trigger.focus()
    const result = open()
    await screen.findByRole('alertdialog')
    await userEvent.keyboard('{Escape}')
    await result
    expect(document.activeElement).toBe(trigger)
    trigger.remove()
  })

  it('installHostApi exposes confirmAction on window.hoaHost', () => {
    installHostApi()
    expect(window.hoaHost?.confirmAction).toBe(confirmAction)
  })
})
