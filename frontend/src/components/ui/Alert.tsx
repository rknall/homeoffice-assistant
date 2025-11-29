// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AlertProps {
  variant?: 'info' | 'success' | 'warning' | 'error'
  title?: string
  children: ReactNode
  className?: string
}

const icons = {
  info: Info,
  success: CheckCircle,
  warning: AlertCircle,
  error: XCircle,
}

const styles = {
  info: 'bg-blue-50 text-blue-800 border-blue-200',
  success: 'bg-green-50 text-green-800 border-green-200',
  warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
  error: 'bg-red-50 text-red-800 border-red-200',
}

const iconStyles = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
}

export function Alert({ variant = 'info', title, children, className }: AlertProps) {
  const Icon = icons[variant]

  return (
    <div
      className={cn(
        'rounded-md border p-4',
        styles[variant],
        className
      )}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={cn('h-5 w-5', iconStyles[variant])} />
        </div>
        <div className="ml-3">
          {title && <h3 className="text-sm font-medium mb-1">{title}</h3>}
          <div className="text-sm">{children}</div>
        </div>
      </div>
    </div>
  )
}
