// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { forwardRef, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const textareaId = id || props.name

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={textareaId} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            'block w-full rounded-lg bg-white px-3 py-2.5',
            'border border-gray-300 shadow-sm',
            'text-gray-900 placeholder:text-gray-400',
            'transition-all duration-150 ease-in-out',
            'hover:border-gray-400',
            'focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'min-h-[80px] resize-y',
            error &&
              'border-red-500 hover:border-red-500 focus:border-red-500 focus:ring-red-500/20',
            className,
          )}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>
    )
  },
)

Textarea.displayName = 'Textarea'
