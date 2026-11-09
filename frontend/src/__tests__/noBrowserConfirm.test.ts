// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { describe, expect, it } from 'vitest'

const BROWSER_CONFIRM = /(^|[^\w.])confirm\(|window\.confirm\(/

// Every .ts/.tsx source of the host app and of the plugin frontends. Built
// bundles (index.js), node_modules and dist are not matched.
const sources = import.meta.glob<string>(
  [
    '../**/*.{ts,tsx}',
    '../../../plugins/*/frontend/**/*.{ts,tsx}',
    '!**/node_modules/**',
    '!**/dist/**',
    '!**/noBrowserConfirm.test.ts',
  ],
  { query: '?raw', import: 'default', eager: true },
)

describe('no browser confirm dialog', () => {
  it('finds the source files it is meant to scan', () => {
    const paths = Object.keys(sources)
    expect(paths.some((p) => p.includes('/plugins/time-tracking/frontend/'))).toBe(true)
    expect(paths.some((p) => p.endsWith('/pages/Companies.tsx'))).toBe(true)
  })

  it('uses confirmAction instead of confirm() in every source file', () => {
    const offenders = Object.entries(sources)
      .filter(([, text]) => BROWSER_CONFIRM.test(text))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })
})
