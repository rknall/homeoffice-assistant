// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { TemplateReason } from '@/types'

/** Insert text at the cursor of the focused textarea or input and notify React. */
function insertVariable(variable: string) {
  // Get the active textarea and insert the variable at cursor
  const activeElement = document.activeElement as HTMLTextAreaElement | HTMLInputElement
  if (
    activeElement &&
    (activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'INPUT')
  ) {
    const start = activeElement.selectionStart || 0
    const end = activeElement.selectionEnd || 0
    const currentValue = activeElement.value
    const newValue = currentValue.substring(0, start) + variable + currentValue.substring(end)
    activeElement.value = newValue
    activeElement.setSelectionRange(start + variable.length, start + variable.length)
    activeElement.focus()

    // Trigger React's onChange
    const event = new Event('input', { bubbles: true })
    activeElement.dispatchEvent(event)
  }
}

export function EmailTemplateVariables({ reason }: { reason: TemplateReason | undefined }) {
  return (
    <div className="w-64 flex-shrink-0 border-l border-gray-200 pl-6">
      <h3 className="font-medium text-gray-900 mb-4">Available Variables</h3>
      {reason ? (
        <div className="space-y-3">
          {reason.variables.map((v) => (
            <div key={v.variable} className="text-sm">
              <button
                type="button"
                onClick={() => insertVariable(v.variable)}
                className="font-mono text-blue-600 hover:text-blue-800 cursor-pointer"
                title={`Click to insert: ${v.variable}`}
              >
                {v.variable}
              </button>
              <p className="text-gray-500 text-xs">{v.description}</p>
              <p className="text-gray-400 text-xs">e.g. {v.example}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">Select a template type to see available variables</p>
      )}
    </div>
  )
}
