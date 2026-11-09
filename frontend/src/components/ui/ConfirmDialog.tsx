// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { type KeyboardEvent, useEffect, useId, useRef } from 'react'
import { Button } from '@/components/ui/Button'
import { type ConfirmOptions, useConfirm } from '@/stores/confirm'

interface ConfirmDialogProps {
  options: ConfirmOptions
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ options, onConfirm, onCancel }: ConfirmDialogProps) {
  const variant = options.variant ?? 'danger'
  const confirmLabel = options.confirmLabel ?? (variant === 'danger' ? 'Delete' : 'Confirm')
  const cancelLabel = options.cancelLabel ?? 'Cancel'
  const titleId = useId()
  const descId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)
  const confirmRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    ;(variant === 'danger' ? cancelRef : confirmRef).current?.focus()
    return () => previous?.focus()
  }, [variant])

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      onCancel()
    } else if (event.key === 'Tab') {
      // Keep focus between the two buttons.
      const first = cancelRef.current
      const last = confirmRef.current
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
  }

  return (
    <>
      <button
        type="button"
        tabIndex={-1}
        className="fixed inset-0 bg-black/50 z-40 cursor-default"
        onClick={onCancel}
        aria-label="Dismiss dialog"
        data-testid="confirm-backdrop"
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descId}
          onKeyDown={handleKeyDown}
          className="bg-white rounded-lg shadow-xl w-full max-w-sm overflow-hidden pointer-events-auto"
        >
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 id={titleId} className="text-lg font-semibold text-gray-900">
              {options.title}
            </h2>
          </div>
          <div className="p-6">
            <p id={descId} className="text-gray-600">
              {options.message}
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button ref={cancelRef} variant="secondary" onClick={onCancel}>
                {cancelLabel}
              </Button>
              <Button
                ref={confirmRef}
                variant={variant === 'danger' ? 'danger' : 'primary'}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export function ConfirmDialogHost() {
  const request = useConfirm((state) => state.request)
  const settle = useConfirm((state) => state.settle)
  if (!request) return null
  return (
    <ConfirmDialog
      options={request.options}
      onConfirm={() => settle(true)}
      onCancel={() => settle(false)}
    />
  )
}
