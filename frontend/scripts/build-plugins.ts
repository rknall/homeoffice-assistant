// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Build script for frontend plugin bundles.
 *
 * This script compiles TypeScript plugin sources to JavaScript bundles
 * that can be dynamically loaded at runtime by the plugin loader.
 */

import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'
import * as esbuild from 'esbuild'

const Filename = fileURLToPath(import.meta.url)
const Dirname = path.dirname(Filename)

const PLUGINS_DIR = path.resolve(Dirname, '../../plugins')
const REACT_SHIM = path.resolve(Dirname, 'react-shim.js')

// Find all plugins with frontend/index.ts
function findPlugins(): string[] {
  const plugins: string[] = []

  if (!fs.existsSync(PLUGINS_DIR)) {
    console.log('No plugins directory found')
    return plugins
  }

  const entries = fs.readdirSync(PLUGINS_DIR, { withFileTypes: true })
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const frontendIndex = path.join(PLUGINS_DIR, entry.name, 'frontend', 'index.ts')
      if (fs.existsSync(frontendIndex)) {
        plugins.push(entry.name)
      }
    }
  }

  return plugins
}

// Build a single plugin
async function buildPlugin(pluginId: string): Promise<void> {
  const entryPoint = path.join(PLUGINS_DIR, pluginId, 'frontend', 'index.ts')
  const outFile = path.join(PLUGINS_DIR, pluginId, 'frontend', 'index.js')

  console.log(`Building ${pluginId}...`)

  await esbuild.build({
    entryPoints: [entryPoint],
    bundle: true,
    outfile: outFile,
    format: 'esm',
    platform: 'browser',
    target: 'es2020',
    minify: process.env.NODE_ENV === 'production',
    sourcemap: process.env.NODE_ENV !== 'production',
    // Use alias to point React imports to our shim that uses window.React
    alias: {
      react: REACT_SHIM,
      'react-dom': REACT_SHIM,
      'react/jsx-runtime': REACT_SHIM,
    },
    define: {
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    },
    // Use automatic JSX runtime
    jsx: 'automatic',
    loader: {
      '.tsx': 'tsx',
      '.ts': 'ts',
    },
  })

  console.log(`  → ${outFile}`)
}

// Main
async function main() {
  const plugins = findPlugins()

  if (plugins.length === 0) {
    console.log('No plugins with TypeScript frontends found')
    return
  }

  console.log(`Found ${plugins.length} plugin(s) to build:\n`)

  for (const plugin of plugins) {
    try {
      await buildPlugin(plugin)
    } catch (error) {
      console.error(`Failed to build ${plugin}:`, error)
      process.exit(1)
    }
  }

  console.log('\nAll plugins built successfully!')
}

main().catch((error) => {
  console.error('Build failed:', error)
  process.exit(1)
})
