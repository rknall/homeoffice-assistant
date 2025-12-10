// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { LoadedPlugin, PluginExports, PluginSummary } from './types'

/**
 * Plugin loader for dynamically importing frontend plugin modules.
 *
 * Plugins are served from /plugin-assets/{plugin_id}/frontend/index.js
 * and must export a default object conforming to PluginExports.
 */
export class PluginLoader {
  private loadedPlugins: Map<string, LoadedPlugin> = new Map()
  private loadingPromises: Map<string, Promise<LoadedPlugin>> = new Map()

  /**
   * Get the URL for a plugin's frontend module.
   * Plugin assets are served from /plugin-assets/* while routes are /plugins/*
   */
  private getPluginUrl(pluginId: string): string {
    return `/plugin-assets/${pluginId}/frontend/index.js`
  }

  /**
   * Load a plugin's frontend module.
   */
  async loadPlugin(plugin: PluginSummary): Promise<LoadedPlugin> {
    const pluginId = plugin.plugin_id

    // Return cached plugin if already loaded
    const cached = this.loadedPlugins.get(pluginId)
    if (cached) {
      return cached
    }

    // Return existing loading promise if in progress
    const existingPromise = this.loadingPromises.get(pluginId)
    if (existingPromise) {
      return existingPromise
    }

    // Create loading promise
    const loadPromise = this.doLoadPlugin(plugin)
    this.loadingPromises.set(pluginId, loadPromise)

    try {
      const loaded = await loadPromise
      this.loadedPlugins.set(pluginId, loaded)
      return loaded
    } finally {
      this.loadingPromises.delete(pluginId)
    }
  }

  /**
   * Actually load the plugin module.
   */
  private async doLoadPlugin(plugin: PluginSummary): Promise<LoadedPlugin> {
    const pluginId = plugin.plugin_id

    if (!plugin.has_frontend) {
      // Plugin has no frontend, return a placeholder
      return {
        id: pluginId,
        manifest: plugin.manifest!,
        exports: {
          manifest: plugin.manifest!,
        },
        isLoaded: true,
      }
    }

    try {
      const url = this.getPluginUrl(pluginId)
      // Use dynamic import with cache busting based on version
      const moduleUrl = `${url}?v=${plugin.plugin_version}`
      const module = await import(/* @vite-ignore */ moduleUrl)

      const exports: PluginExports = module.default || module

      // Validate exports
      if (!exports.manifest) {
        throw new Error('Plugin module must export a manifest')
      }

      // Call onLoad lifecycle hook if provided
      if (exports.onLoad) {
        await exports.onLoad()
      }

      return {
        id: pluginId,
        manifest: exports.manifest,
        exports,
        isLoaded: true,
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error loading plugin'

      console.error(`Failed to load plugin ${pluginId}:`, error)

      return {
        id: pluginId,
        manifest: plugin.manifest!,
        exports: {
          manifest: plugin.manifest!,
        },
        isLoaded: false,
        loadError: errorMessage,
      }
    }
  }

  /**
   * Unload a plugin.
   */
  async unloadPlugin(pluginId: string): Promise<void> {
    const plugin = this.loadedPlugins.get(pluginId)

    if (plugin?.exports.onUnload) {
      try {
        await plugin.exports.onUnload()
      } catch (error) {
        console.error(`Error in onUnload for plugin ${pluginId}:`, error)
      }
    }

    this.loadedPlugins.delete(pluginId)
  }

  /**
   * Get a loaded plugin by ID.
   */
  getPlugin(pluginId: string): LoadedPlugin | undefined {
    return this.loadedPlugins.get(pluginId)
  }

  /**
   * Get all loaded plugins.
   */
  getAllPlugins(): LoadedPlugin[] {
    return Array.from(this.loadedPlugins.values())
  }

  /**
   * Check if a plugin is loaded.
   */
  isLoaded(pluginId: string): boolean {
    return this.loadedPlugins.has(pluginId)
  }

  /**
   * Unload all plugins.
   */
  async unloadAll(): Promise<void> {
    const pluginIds = Array.from(this.loadedPlugins.keys())
    await Promise.all(pluginIds.map((id) => this.unloadPlugin(id)))
  }
}

// Singleton instance
export const pluginLoader = new PluginLoader()
