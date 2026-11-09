// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Alert } from '@/components/ui/Alert'
import type { RestoreValidationResponse } from '@/types'
import { formatBytes } from './formatBytes'

export function RestoreValidationAlert({ result }: { result: RestoreValidationResponse }) {
  return (
    <Alert variant={result.valid ? 'success' : 'error'} className="mt-4">
      <div>{result.message}</div>
      {result.warnings.length > 0 && (
        <ul className="mt-2 list-disc list-inside">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      {result.metadata && result.valid && (
        <div className="mt-2 text-xs">
          <p>Format: {result.metadata.backup_format_version}</p>
          {result.metadata.created_at && (
            <p>Created: {new Date(result.metadata.created_at).toLocaleString()}</p>
          )}
          <p>Created by: {result.metadata.created_by}</p>
          <p>Database size: {formatBytes(result.metadata.db_size_bytes)}</p>
          <p>Avatars: {result.metadata.avatar_count}</p>
          {result.metadata.integration_config_count > 0 && (
            <p>Integration configs: {result.metadata.integration_config_count}</p>
          )}
          {result.metadata.is_password_protected && (
            <p className="text-green-600">Password verified</p>
          )}
        </div>
      )}
    </Alert>
  )
}
