// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useBreadcrumb } from '@/stores/breadcrumb'

export function Breadcrumb() {
  const { items } = useBreadcrumb()

  if (items.length === 0) {
    return null
  }

  return (
    <nav className="flex items-center text-sm text-gray-500 mb-4">
      <Link to="/" className="hover:text-gray-700">
        Dashboard
      </Link>
      {items.map((item, index) => (
        <span key={index} className="flex items-center">
          <ChevronRight className="h-4 w-4 mx-2 text-gray-400" />
          {item.href ? (
            <Link to={item.href} className="hover:text-gray-700">
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900 font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
