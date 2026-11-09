// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PluginWidgetSlot } from './PluginWidgetSlot'
import { usePlugins } from './registry'
import type { LoadedPlugin, PluginExports } from './types'

function loaded(id: string, exports: Partial<PluginExports>, isLoaded = true): LoadedPlugin {
  const manifest = {
    id,
    name: id,
    version: '1.0.0',
    description: '',
    capabilities: { backend: true, frontend: true, config: false },
    permissions: [],
  }
  return { id, manifest, exports: { manifest, ...exports }, isLoaded }
}

describe('PluginWidgetSlot', () => {
  afterEach(() => {
    cleanup()
    usePlugins.setState({ loadedPlugins: [] })
  })

  it('renders the companyDetail widget of loaded plugins with the company id', () => {
    usePlugins.setState({
      loadedPlugins: [
        loaded('a', { widgets: { companyDetail: ({ companyId }) => <p>widget {companyId}</p> } }),
        loaded('b', {}),
        loaded('c', { widgets: { companyDetail: () => <p>not loaded</p> } }, false),
      ],
    })
    render(<PluginWidgetSlot companyId="co-1" />)
    expect(screen.getByText('widget co-1')).toBeTruthy()
    expect(screen.queryByText('not loaded')).toBeNull()
  })

  it('renders nothing without plugins', () => {
    usePlugins.setState({ loadedPlugins: [] })
    const { container } = render(<PluginWidgetSlot companyId="co-1" />)
    expect(container.innerHTML).toBe('')
  })
})
