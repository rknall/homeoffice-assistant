// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Footer } from './Footer'
import { Breadcrumb } from '@/components/ui/Breadcrumb'

export function Layout() {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-auto">
          <div className="p-6">
            <Breadcrumb />
            <Outlet />
          </div>
        </main>
        <Footer />
      </div>
    </div>
  )
}
