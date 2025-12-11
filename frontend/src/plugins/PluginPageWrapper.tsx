// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { type ComponentType, useEffect } from 'react'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { PluginManifest } from './types'

interface PluginPageWrapperProps {
  manifest: PluginManifest
  component: ComponentType
}

/**
 * Wrapper component for plugin pages that sets up breadcrumb navigation.
 */
export function PluginPageWrapper({ manifest, component: Component }: PluginPageWrapperProps) {
  const { setItems } = useBreadcrumb()

  useEffect(() => {
    setItems([{ label: manifest.name }])

    // Cleanup on unmount
    return () => {
      setItems([])
    }
  }, [manifest.name, setItems])

  return <Component />
}
