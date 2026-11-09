// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { TemplatePreviewResponse } from '@/types'

interface EmailTemplatePreviewProps {
  isLoading: boolean
  preview: TemplatePreviewResponse | null
}

export function EmailTemplatePreview({ isLoading, preview }: EmailTemplatePreviewProps) {
  return isLoading ? (
    <div className="flex-1 flex items-center justify-center text-gray-500">Loading preview...</div>
  ) : preview ? (
    <div className="flex-1 flex flex-col overflow-auto">
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium text-gray-500">Subject</p>
        <p className="text-gray-900">{preview.subject}</p>
      </div>
      <div className="flex-1 border rounded-lg overflow-hidden">
        <iframe
          srcDoc={preview.body_html}
          title="Email Preview"
          className="w-full h-full bg-white"
          style={{ minHeight: '300px' }}
        />
      </div>
    </div>
  ) : (
    <div className="flex-1 flex items-center justify-center text-gray-500">
      Enter template content to see preview
    </div>
  )
}
