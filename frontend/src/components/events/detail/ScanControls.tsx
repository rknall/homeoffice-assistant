// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Button } from '@/components/ui/Button'

interface ScanControlsProps {
  isScanning: boolean
  error: string | null
  warnings: string[]
  onScan: () => void
}

/** "Scan Document with AI" button with its error and warning output. */
export function ScanControls({ isScanning, error, warnings, onScan }: ScanControlsProps) {
  return (
    <div className="mb-4">
      <Button
        type="button"
        variant="secondary"
        className="w-full"
        isLoading={isScanning}
        onClick={onScan}
      >
        Scan Document with AI
      </Button>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {warnings.length > 0 && (
        <ul className="mt-2 text-xs text-amber-700 space-y-0.5">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
