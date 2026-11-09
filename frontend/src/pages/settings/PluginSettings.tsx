// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Download, Plus, Settings, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '@/api/client'
import { InstallPluginModal } from '@/components/settings/InstallPluginModal'
import { PluginInfoModal } from '@/components/settings/PluginInfoModal'
import { UninstallPluginModal } from '@/components/settings/UninstallPluginModal'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { usePlugins } from '@/plugins'
import type { DiscoveredPlugin, PluginInfo, PluginSummary } from '@/plugins/types'
import { useBreadcrumb } from '@/stores/breadcrumb'

export function PluginSettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const {
    plugins,
    discoveredPlugins,
    isLoading,
    error: storeError,
    fetchPlugins,
    fetchDiscoveredPlugins,
    installPlugin,
    installDiscoveredPlugin,
    uninstallPlugin,
  } = usePlugins()

  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false)
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false)
  const [isUninstallModalOpen, setIsUninstallModalOpen] = useState(false)
  const [selectedPlugin, setSelectedPlugin] = useState<PluginSummary | null>(null)
  const [pluginInfo, setPluginInfo] = useState<PluginInfo | null>(null)
  const [isLoadingInfo, setIsLoadingInfo] = useState(false)
  const [dropTables, setDropTables] = useState(false)
  const [removePermissions, setRemovePermissions] = useState(false)
  const [deleteFiles, setDeleteFiles] = useState(false)
  const [upgradeMode, setUpgradeMode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState<string | null>(null)

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Plugins' }])
  }, [setBreadcrumb])

  const loadPlugins = useCallback(async () => {
    try {
      await Promise.all([fetchPlugins(), fetchDiscoveredPlugins()])
    } catch (e) {
      setError(errorMessage(e, 'Failed to load plugins'))
    }
  }, [fetchPlugins, fetchDiscoveredPlugins])

  useEffect(() => {
    loadPlugins()
  }, [loadPlugins])

  const handleInstallDiscoveredPlugin = async (plugin: DiscoveredPlugin) => {
    setIsProcessing(plugin.plugin_id)
    setError(null)
    try {
      const result = await installDiscoveredPlugin(plugin.plugin_id)
      setSuccessMessage(`Plugin "${result.plugin_name}" installed successfully`)
    } catch (err) {
      setError(errorMessage(err, 'Failed to install plugin'))
    } finally {
      setIsProcessing(null)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.zip')) {
      setError('Please upload a ZIP file')
      return
    }

    setIsProcessing('install')
    setError(null)
    try {
      const result = await installPlugin(file, upgradeMode)
      setSuccessMessage(result.message)
      setIsInstallModalOpen(false)
      setUpgradeMode(false)
    } catch (err) {
      setError(errorMessage(err, 'Failed to install plugin'))
    } finally {
      setIsProcessing(null)
      // Reset file input
      e.target.value = ''
    }
  }

  const openUninstallModal = (plugin: PluginSummary) => {
    setSelectedPlugin(plugin)
    setDropTables(false)
    setRemovePermissions(false)
    setDeleteFiles(false)
    setIsUninstallModalOpen(true)
  }

  const handleUninstall = async () => {
    if (!selectedPlugin) return

    setIsProcessing(selectedPlugin.plugin_id)
    setError(null)
    try {
      // keepFiles is the inverse of deleteFiles (default: keep files)
      await uninstallPlugin(selectedPlugin.plugin_id, dropTables, removePermissions, !deleteFiles)
      const message = deleteFiles
        ? `Plugin "${selectedPlugin.manifest?.name || selectedPlugin.plugin_id}" uninstalled`
        : `Plugin "${selectedPlugin.manifest?.name || selectedPlugin.plugin_id}" uninstalled (files kept for reinstallation)`
      setSuccessMessage(message)
      setIsUninstallModalOpen(false)
      setSelectedPlugin(null)
    } catch (err) {
      setError(errorMessage(err, 'Failed to uninstall plugin'))
    } finally {
      setIsProcessing(null)
    }
  }

  const openConfigModal = async (plugin: PluginSummary) => {
    setSelectedPlugin(plugin)
    setIsLoadingInfo(true)
    setIsConfigModalOpen(true)
    setError(null)
    try {
      const { getPluginInfo } = usePlugins.getState()
      const info = await getPluginInfo(plugin.plugin_id)
      setPluginInfo(info)
    } catch (e) {
      setError(errorMessage(e, 'Failed to load plugin configuration'))
    } finally {
      setIsLoadingInfo(false)
    }
  }

  const closeConfigModal = () => {
    setIsConfigModalOpen(false)
    setSelectedPlugin(null)
    setPluginInfo(null)
  }

  // Clear success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [successMessage])

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Plugins</h1>

      {(error || storeError) && (
        <Alert variant="error" className="mb-4">
          {error || storeError}
        </Alert>
      )}

      {successMessage && (
        <Alert variant="success" className="mb-4">
          {successMessage}
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Installed Plugins</CardTitle>
          <Button onClick={() => setIsInstallModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Install Plugin
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : plugins.length === 0 ? (
            <div className="text-center py-8">
              <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">
                No plugins installed. Install a plugin to extend the application functionality.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {plugins.map((plugin) => (
                <div key={plugin.plugin_id} className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-gray-900">
                          {plugin.manifest?.name || plugin.plugin_id}
                        </h3>
                        {plugin.has_frontend && (
                          <Badge variant="info" className="text-xs">
                            Frontend
                          </Badge>
                        )}
                        {plugin.has_backend && (
                          <Badge variant="info" className="text-xs">
                            Backend
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        {plugin.manifest?.description || 'No description available'}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        <span>Version: {plugin.plugin_version}</span>
                        {plugin.manifest?.author && <span>Author: {plugin.manifest.author}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isProcessing === plugin.plugin_id ? (
                        <Spinner className="h-5 w-5" />
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => openConfigModal(plugin)}
                            title="Configure plugin"
                          >
                            <Settings className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => openUninstallModal(plugin)}
                            title="Uninstall plugin"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available (Discovered) Plugins */}
      {discoveredPlugins.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Available Plugins</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-4">
              These plugins are available on disk but not yet installed.
            </p>
            <div className="divide-y divide-gray-200">
              {discoveredPlugins.map((plugin) => (
                <div key={plugin.plugin_id} className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="font-medium text-gray-900">{plugin.name}</h3>
                        {plugin.has_frontend && (
                          <Badge variant="info" className="text-xs">
                            Frontend
                          </Badge>
                        )}
                        {plugin.has_backend && (
                          <Badge variant="info" className="text-xs">
                            Backend
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{plugin.description}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        <span>Version: {plugin.version}</span>
                        {plugin.author && <span>Author: {plugin.author}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isProcessing === plugin.plugin_id ? (
                        <Spinner className="h-5 w-5" />
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => handleInstallDiscoveredPlugin(plugin)}
                          title="Install plugin"
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Install
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <InstallPluginModal
        isOpen={isInstallModalOpen}
        isInstalling={isProcessing === 'install'}
        upgradeMode={upgradeMode}
        onUpgradeModeChange={setUpgradeMode}
        onFileUpload={handleFileUpload}
        onClose={() => {
          setIsInstallModalOpen(false)
          setUpgradeMode(false)
        }}
      />

      <PluginInfoModal
        isOpen={isConfigModalOpen}
        isLoading={isLoadingInfo}
        pluginInfo={pluginInfo}
        onClose={closeConfigModal}
      />

      <UninstallPluginModal
        isOpen={isUninstallModalOpen}
        plugin={selectedPlugin}
        isProcessing={isProcessing === selectedPlugin?.plugin_id}
        dropTables={dropTables}
        removePermissions={removePermissions}
        deleteFiles={deleteFiles}
        onDropTablesChange={setDropTables}
        onRemovePermissionsChange={setRemovePermissions}
        onDeleteFilesChange={setDeleteFiles}
        onConfirm={handleUninstall}
        onClose={() => {
          setIsUninstallModalOpen(false)
          setSelectedPlugin(null)
        }}
      />
    </div>
  )
}
