import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'

export function Layout() {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          <Breadcrumb />
          <Outlet />
        </div>
      </main>
    </div>
  )
}
