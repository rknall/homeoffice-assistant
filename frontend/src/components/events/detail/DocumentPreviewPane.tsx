// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { FileText } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'

interface DocumentPreviewPaneProps {
  isLoading: boolean
  url: string | null
}

/** Left-hand document preview used next to the expense forms. */
export function DocumentPreviewPane({ isLoading, url }: DocumentPreviewPaneProps) {
  return (
    <div className="flex-1 border rounded-lg overflow-hidden bg-gray-100">
      {isLoading ? (
        <div className="flex items-center justify-center h-full">
          <Spinner />
        </div>
      ) : url ? (
        <iframe src={url} className="w-full h-full" title="Document Preview" />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>Preview not available</p>
          </div>
        </div>
      )}
    </div>
  )
}
