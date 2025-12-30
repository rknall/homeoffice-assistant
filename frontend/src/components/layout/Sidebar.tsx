// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import {
  Building2,
  Calendar,
  ClipboardList,
  FileText,
  Globe,
  HardDrive,
  LayoutDashboard,
  Link2,
  LogOut,
  icons as lucideIcons,
  Mail,
  Puzzle,
  Settings,
  Shield,
  Users,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import logoMark from '@/assets/homeoffice_assistant_logo.svg'
import { cn } from '@/lib/utils'
import type { PluginNavItem } from '@/plugins'
import { usePlugins } from '@/plugins'
import { useAuth } from '@/stores/auth'
import { getAvatarUrl } from '@/utils/gravatar'

type IconComponent = ComponentType<{ className?: string }>

const pluginIconFallback: IconComponent = FileText
const lucideIconMap = lucideIcons as Record<string, IconComponent>

function resolvePluginIcon(icon?: PluginNavItem['icon']): IconComponent | undefined {
  if (!icon) {
    return undefined
  }
  if (typeof icon === 'string') {
    const resolved = lucideIconMap[icon]
    if (resolved) {
      return resolved
    }
    console.warn(`[Sidebar] Unknown plugin icon "${icon}" requested; falling back to default.`)
    return pluginIconFallback
  }
  return icon
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/events', label: 'Events', icon: Calendar },
  { to: '/companies', label: 'Companies', icon: Building2 },
]

const settingsSubItems = [
  { to: '/settings/regional', label: 'Regional', icon: Globe },
  { to: '/settings/integrations', label: 'Integrations', icon: Link2 },
  { to: '/settings/plugins', label: 'Plugins', icon: Puzzle },
  { to: '/settings/templates', label: 'Email Templates', icon: Mail },
  { to: '/settings/todo-templates', label: 'Todo Templates', icon: ClipboardList },
  { to: '/settings/backup', label: 'Backup', icon: HardDrive },
  { to: '/settings/users', label: 'Users', icon: Users },
  { to: '/settings/roles', label: 'Roles', icon: Shield },
]

export function Sidebar() {
  const { user, logout, hasPermission } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  // Select loadedPlugins directly to avoid infinite re-renders from getNavItems()
  const loadedPlugins = usePlugins((state) => state.loadedPlugins)

  const isSettingsRoute = location.pathname.startsWith('/settings')
  const isPluginRoute = location.pathname.startsWith('/plugins')

  // Derive nav items from loaded plugins
  const pluginNavItems = loadedPlugins
    .flatMap((plugin) => {
      if (plugin.isLoaded && plugin.exports.getNavItems) {
        try {
          return plugin.exports.getNavItems()
        } catch {
          return []
        }
      }
      return []
    })
    .sort((a, b) => (a.order ?? 100) - (b.order ?? 100))

  return (
    <div className="flex flex-col w-64 bg-gray-900 text-white">
      <Link
        to="/"
        className="flex items-center h-16 px-4 border-b border-gray-800 transition-colors hover:bg-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
        aria-label="Go to dashboard"
      >
        <img
          src={logoMark}
          alt="HomeOffice Assistant logo"
          className="h-10 w-10 object-contain drop-shadow"
          draggable={false}
        />
        <div className="ml-3 leading-tight">
          <p className="text-base font-semibold tracking-tight">HomeOffice Assistant</p>
          <p className="text-xs text-emerald-200">Your homeoffice co-pilot</p>
        </div>
      </Link>
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
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white',
              )
            }
          >
            <item.icon className="h-5 w-5 mr-3" />
            {item.label}
          </NavLink>
        ))}

        {/* Plugin nav items */}
        {pluginNavItems.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-800 space-y-1">
            {pluginNavItems.map((item) => {
              const IconComponent = resolvePluginIcon(item.icon)

              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive || (isPluginRoute && item.path.includes(location.pathname))
                        ? 'bg-gray-800 text-white'
                        : 'text-gray-300 hover:bg-gray-800 hover:text-white',
                    )
                  }
                >
                  {IconComponent && <IconComponent className="h-5 w-5 mr-3" />}
                  {item.label}
                </NavLink>
              )
            })}
          </div>
        )}

        {/* Settings with sub-navigation */}
        {user && hasPermission('system.admin') && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <NavLink
              to="/settings"
              className={cn(
                'flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isSettingsRoute
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white',
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
                          : 'text-gray-400 hover:text-white hover:bg-gray-800',
                      )
                    }
                  >
                    <item.icon className="h-4 w-4 mr-2" />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        )}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <button
          type="button"
          onClick={() => user && navigate(`/settings/users/${user.id}`)}
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
          type="button"
          onClick={() => logout()}
          className="flex items-center w-full px-3 py-2 text-sm text-gray-300 rounded-md hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut className="h-5 w-5 mr-3" />
          Sign out
        </button>
      </div>
    </div>
  )
}
