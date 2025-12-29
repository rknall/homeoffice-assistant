// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronDown, ChevronRight } from 'lucide-react'
import { type ReactNode, useState } from 'react'

interface TimelineGroupProps {
  title: string
  count: number
  children: ReactNode
  defaultOpen?: boolean
  variant?: 'default' | 'muted'
}

export function TimelineGroup({
  title,
  count,
  children,
  defaultOpen = true,
  variant = 'default',
}: TimelineGroupProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  if (count === 0) {
    return null
  }

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 mb-3 w-full text-left group"
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
        <span
          className={`text-sm font-semibold uppercase tracking-wider ${
            variant === 'muted' ? 'text-gray-400' : 'text-gray-600'
          }`}
        >
          {title}
        </span>
        <span className="text-xs text-gray-400">({count})</span>
      </button>

      {isOpen && <div className="space-y-3">{children}</div>}
    </div>
  )
}
