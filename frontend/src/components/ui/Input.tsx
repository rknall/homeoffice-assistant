// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  description?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, description, id, ...props }, ref) => {
    const inputId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'block w-full rounded-lg bg-white px-3 py-2.5',
            'border border-gray-300 shadow-sm',
            'text-gray-900 placeholder:text-gray-400',
            'transition-all duration-150 ease-in-out',
            'hover:border-gray-400',
            'focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            error && 'border-red-500 hover:border-red-500 focus:border-red-500 focus:ring-red-500/20',
            className
          )}
          {...props}
        />
        {description && !error && (
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        )}
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'
