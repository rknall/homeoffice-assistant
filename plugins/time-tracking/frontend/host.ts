// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { PluginHostApi } from '../../../frontend/src/plugins/hostApi'

type ConfirmOptions = Parameters<PluginHostApi['confirmAction']>[0]

/**
 * Ask the user to confirm an action through the host application's dialog.
 *
 * Rejects when the host API is missing; there is no browser dialog fallback.
 */
export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  const host = window.hoaHost
  if (!host) {
    return Promise.reject(new Error('Host confirm dialog is not available'))
  }
  return host.confirmAction(options)
}
