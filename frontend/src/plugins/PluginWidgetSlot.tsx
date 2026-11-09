// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { usePlugins } from './registry'

interface PluginWidgetSlotProps {
  companyId: string
}

/**
 * Renders the `widgets.companyDetail` component of every loaded plugin.
 */
export function PluginWidgetSlot({ companyId }: PluginWidgetSlotProps) {
  const loadedPlugins = usePlugins((state) => state.loadedPlugins)

  return (
    <>
      {loadedPlugins.map((plugin) => {
        const Widget = plugin.isLoaded ? plugin.exports.widgets?.companyDetail : undefined
        return Widget ? (
          <div key={plugin.id} className="mt-6">
            <Widget companyId={companyId} />
          </div>
        ) : null
      })}
    </>
  )
}
