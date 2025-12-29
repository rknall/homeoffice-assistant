// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { createContext, type ReactNode, useContext, useState } from 'react'
import { cn } from '@/lib/utils'

interface TabsContextValue {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const TabsContext = createContext<TabsContextValue | null>(null)

function useTabsContext() {
  const context = useContext(TabsContext)
  if (!context) {
    throw new Error('Tabs components must be used within a Tabs provider')
  }
  return context
}

interface TabsProps {
  defaultTab: string
  children: ReactNode
  className?: string
  onChange?: (tab: string) => void
}

export function Tabs({ defaultTab, children, className, onChange }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab)

  const handleSetActiveTab = (tab: string) => {
    setActiveTab(tab)
    onChange?.(tab)
  }

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab: handleSetActiveTab }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

interface TabListProps {
  children: ReactNode
  className?: string
}

export function TabList({ children, className }: TabListProps) {
  return (
    <div className={cn('flex border-b border-gray-200 bg-white', className)} role="tablist">
      {children}
    </div>
  )
}

interface TabProps {
  value: string
  children: ReactNode
  badge?: number | string
  className?: string
}

export function Tab({ value, children, badge, className }: TabProps) {
  const { activeTab, setActiveTab } = useTabsContext()
  const isActive = activeTab === value

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={() => setActiveTab(value)}
      className={cn(
        'px-4 py-3 text-sm font-medium transition-colors relative',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
        isActive
          ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50',
        className,
      )}
    >
      {children}
      {badge !== undefined && badge !== 0 && (
        <span
          className={cn(
            'ml-2 px-2 py-0.5 text-xs rounded-full',
            isActive ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700',
          )}
        >
          {badge}
        </span>
      )}
    </button>
  )
}

interface TabPanelProps {
  value: string
  children: ReactNode
  className?: string
}

export function TabPanel({ value, children, className }: TabPanelProps) {
  const { activeTab } = useTabsContext()

  if (activeTab !== value) {
    return null
  }

  return (
    <div role="tabpanel" className={className}>
      {children}
    </div>
  )
}
