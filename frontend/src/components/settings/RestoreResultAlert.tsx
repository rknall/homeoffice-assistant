// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Alert } from '@/components/ui/Alert'
import type { RestoreResponse } from '@/types'

export function RestoreResultAlert({ result }: { result: RestoreResponse }) {
  return (
    <Alert variant={result.success ? 'success' : 'error'} className="mb-4">
      <div>{result.message}</div>
      {result.success && (
        <>
          {result.migrations_run && <div className="mt-2 text-sm">{result.migrations_message}</div>}
          {result.configs_imported > 0 && (
            <div className="mt-1 text-sm">
              {result.configs_imported} integration config(s) imported.
            </div>
          )}
          {result.requires_restart && (
            <div className="mt-2 font-medium">
              Please restart the application now to apply the restored data.
            </div>
          )}
        </>
      )}
    </Alert>
  )
}
