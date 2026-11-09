// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { create } from 'zustand'

export interface ConfirmOptions {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'primary'
}

interface ConfirmRequest {
  options: ConfirmOptions
  resolve: (confirmed: boolean) => void
}

interface ConfirmState {
  request: ConfirmRequest | null
  settle: (confirmed: boolean) => void
}

export const useConfirm = create<ConfirmState>((set, get) => ({
  request: null,
  settle: (confirmed: boolean) => {
    const current = get().request
    if (!current) return
    set({ request: null })
    current.resolve(confirmed)
  },
}))

/**
 * Open the confirm dialog and wait for the answer.
 *
 * A call while another dialog is open resolves the earlier one with false.
 */
export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  useConfirm.getState().settle(false)
  return new Promise<boolean>((resolve) => {
    useConfirm.setState({ request: { options, resolve } })
  })
}
