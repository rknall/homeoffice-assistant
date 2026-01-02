// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Package script for creating distributable plugin zip files.
 *
 * Creates a zip containing only the files needed for installation:
 * - plugin.manifest.json
 * - backend/ (Python files, excluding __pycache__)
 * - frontend/index.js and index.js.map (built bundles only)
 *
 * Usage:
 *   npm run package:plugin -- <plugin-id>
 *   npm run package:plugin -- time-tracking
 *   npm run package:plugins  (packages all plugins)
 */

import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'
import archiver from 'archiver'

const Filename = fileURLToPath(import.meta.url)
const Dirname = path.dirname(Filename)

const PLUGINS_DIR = path.resolve(Dirname, '../../plugins')
const DIST_DIR = path.resolve(Dirname, '../../dist/plugins')

interface PluginManifest {
  id: string
  name: string
  version: string
}

function readManifest(pluginDir: string): PluginManifest | null {
  const manifestPath = path.join(pluginDir, 'plugin.manifest.json')
  if (!fs.existsSync(manifestPath)) {
    return null
  }
  return JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))
}

function findAllPlugins(): string[] {
  const plugins: string[] = []

  if (!fs.existsSync(PLUGINS_DIR)) {
    return plugins
  }

  const entries = fs.readdirSync(PLUGINS_DIR, { withFileTypes: true })
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const manifestPath = path.join(PLUGINS_DIR, entry.name, 'plugin.manifest.json')
      if (fs.existsSync(manifestPath)) {
        plugins.push(entry.name)
      }
    }
  }

  return plugins
}

async function packagePlugin(pluginId: string): Promise<string | null> {
  const pluginDir = path.join(PLUGINS_DIR, pluginId)

  if (!fs.existsSync(pluginDir)) {
    console.error(`Plugin directory not found: ${pluginDir}`)
    return null
  }

  const manifest = readManifest(pluginDir)
  if (!manifest) {
    console.error(`No plugin.manifest.json found in ${pluginDir}`)
    return null
  }

  // Ensure dist directory exists
  if (!fs.existsSync(DIST_DIR)) {
    fs.mkdirSync(DIST_DIR, { recursive: true })
  }

  const zipName = `${pluginId}-${manifest.version}.zip`
  const zipPath = path.join(DIST_DIR, zipName)

  // Remove existing zip if present
  if (fs.existsSync(zipPath)) {
    fs.unlinkSync(zipPath)
  }

  console.log(`Packaging ${pluginId} v${manifest.version}...`)

  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(zipPath)
    const archive = archiver('zip', { zlib: { level: 9 } })

    output.on('close', () => {
      const sizeKb = (archive.pointer() / 1024).toFixed(1)
      console.log(`  → ${zipPath} (${sizeKb} KB)`)
      resolve(zipPath)
    })

    archive.on('error', (err) => {
      reject(err)
    })

    archive.pipe(output)

    // Add plugin.manifest.json
    archive.file(path.join(pluginDir, 'plugin.manifest.json'), {
      name: `${pluginId}/plugin.manifest.json`,
    })

    // Add backend Python files (excluding __pycache__)
    const backendDir = path.join(pluginDir, 'backend')
    if (fs.existsSync(backendDir)) {
      archive.glob(
        '**/*.py',
        {
          cwd: backendDir,
          ignore: ['__pycache__/**', '**/__pycache__/**'],
        },
        { prefix: `${pluginId}/backend` },
      )

      // Add migrations non-Python files (script.py.mako)
      const migrationsDir = path.join(backendDir, 'migrations')
      if (fs.existsSync(migrationsDir)) {
        archive.glob(
          '**/*.mako',
          {
            cwd: migrationsDir,
          },
          { prefix: `${pluginId}/backend/migrations` },
        )
      }
    }

    // Add built frontend files only
    const frontendDir = path.join(pluginDir, 'frontend')
    if (fs.existsSync(frontendDir)) {
      const indexJs = path.join(frontendDir, 'index.js')
      const indexJsMap = path.join(frontendDir, 'index.js.map')

      if (fs.existsSync(indexJs)) {
        archive.file(indexJs, { name: `${pluginId}/frontend/index.js` })
      }
      if (fs.existsSync(indexJsMap)) {
        archive.file(indexJsMap, { name: `${pluginId}/frontend/index.js.map` })
      }
    }

    archive.finalize()
  })
}

async function main() {
  const args = process.argv.slice(2)

  let pluginsToPackage: string[]

  if (args.length > 0 && args[0] !== '--all') {
    // Package specific plugin
    pluginsToPackage = [args[0]]
  } else {
    // Package all plugins
    pluginsToPackage = findAllPlugins()
  }

  if (pluginsToPackage.length === 0) {
    console.log('No plugins found to package')
    return
  }

  console.log(`Packaging ${pluginsToPackage.length} plugin(s):\n`)

  const results: { plugin: string; success: boolean; path?: string }[] = []

  for (const plugin of pluginsToPackage) {
    try {
      const zipPath = await packagePlugin(plugin)
      results.push({
        plugin,
        success: zipPath !== null,
        path: zipPath ?? undefined,
      })
    } catch (error) {
      console.error(`Failed to package ${plugin}:`, error)
      results.push({ plugin, success: false })
    }
  }

  console.log('\n--- Summary ---')
  for (const result of results) {
    if (result.success) {
      console.log(`✓ ${result.plugin}: ${result.path}`)
    } else {
      console.log(`✗ ${result.plugin}: failed`)
    }
  }

  const failed = results.filter((r) => !r.success)
  if (failed.length > 0) {
    process.exit(1)
  }
}

main().catch((error) => {
  console.error('Packaging failed:', error)
  process.exit(1)
})
