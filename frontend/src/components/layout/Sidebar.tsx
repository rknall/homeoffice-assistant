// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Building2, Calendar, Globe, LayoutDashboard, Link2, LogOut, Mail, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/stores/auth'
import { getAvatarUrl } from '@/utils/gravatar'
import { ProfileEditModal } from '@/components/ProfileEditModal'
import logoImage from '@/assets/logo.png'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/events', label: 'Events', icon: Calendar },
  { to: '/companies', label: 'Companies', icon: Building2 },
]

const settingsSubItems = [
  { to: '/settings/regional', label: 'Regional', icon: Globe },
  { to: '/settings/integrations', label: 'Integrations', icon: Link2 },
  { to: '/settings/templates', label: 'Email Templates', icon: Mail },
]

export function Sidebar() {
  const { user, logout, setUser } = useAuth()
  const location = useLocation()
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false)

  const isSettingsRoute = location.pathname.startsWith('/settings')

  return (
    <>
      <div className="flex flex-col w-64 bg-gray-900 text-white">
        <div className="flex items-center h-16 px-4 border-b border-gray-800">
          <img
            src={logoImage}
            alt="Travel Manager"
            className="h-10 w-10 object-contain"
          />
          <h1 className="text-xl font-bold ml-2">Travel Manager</h1>
        </div>
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <item.icon className="h-5 w-5 mr-3" />
              {item.label}
            </NavLink>
          ))}

          {/* Settings with sub-navigation */}
          {user?.is_admin && (
            <>
              <NavLink
                to="/settings"
                className={cn(
                  'flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isSettingsRoute
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )}
              >
                <Settings className="h-5 w-5 mr-3" />
                Settings
              </NavLink>

              {isSettingsRoute && (
                <div className="ml-8 space-y-1">
                  {settingsSubItems.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center px-3 py-1.5 rounded-md text-sm transition-colors',
                          isActive
                            ? 'text-white bg-gray-700'
                            : 'text-gray-400 hover:text-white hover:bg-gray-800'
                        )
                      }
                    >
                      <item.icon className="h-4 w-4 mr-2" />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </>
          )}
        </nav>
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={() => setIsProfileModalOpen(true)}
            className="flex items-center w-full mb-3 p-2 -m-2 rounded-lg hover:bg-gray-800 transition-colors cursor-pointer"
          >
            {user && (
              <>
                <img
                  src={getAvatarUrl(user, 64)}
                  alt={user.full_name || user.username}
                  className="w-8 h-8 rounded-full object-cover"
                />
                <div className="ml-3 text-left">
                  <p className="text-sm font-medium">{user.full_name || user.username}</p>
                  <p className="text-xs text-gray-400">{user.email}</p>
                </div>
              </>
            )}
          </button>
          <button
            onClick={() => logout()}
            className="flex items-center w-full px-3 py-2 text-sm text-gray-300 rounded-md hover:bg-gray-800 hover:text-white transition-colors"
          >
            <LogOut className="h-5 w-5 mr-3" />
            Sign out
          </button>
        </div>
      </div>

      {user && (
        <ProfileEditModal
          isOpen={isProfileModalOpen}
          onClose={() => setIsProfileModalOpen(false)}
          user={user}
          onUpdate={setUser}
        />
      )}
    </>
  )
}
