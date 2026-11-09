// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { confirmAction } from '@/stores/confirm'

export const hostApi = { confirmAction }

export type PluginHostApi = typeof hostApi

declare global {
  interface Window {
    hoaHost?: PluginHostApi
  }
}

/** Expose host helpers to plugin bundles, which only import react. */
export function installHostApi(): void {
  window.hoaHost = hostApi
}
