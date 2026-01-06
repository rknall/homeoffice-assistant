// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Download, Plus, Settings, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { usePlugins } from "@/plugins";
import type {
	DiscoveredPlugin,
	PluginInfo,
	PluginSummary,
} from "@/plugins/types";
import { useBreadcrumb } from "@/stores/breadcrumb";

/**
 * Build a warning message for destructive uninstall options.
 */
function buildUninstallWarning(
	dropTables: boolean,
	removePermissions: boolean,
	deleteFiles: boolean,
): string {
	const actions: string[] = [];
	if (dropTables)
		actions.push("permanently delete all data stored by this plugin");
	if (removePermissions)
		actions.push("remove its custom permissions from roles");
	if (deleteFiles) actions.push("delete plugin files from disk");

	if (actions.length === 0) return "";
	if (actions.length === 1) return `This will ${actions[0]}.`;
	const last = actions.pop();
	return `This will ${actions.join(", ")} and ${last}.`;
}

export function PluginSettings() {
	const { setItems: setBreadcrumb } = useBreadcrumb();
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
	} = usePlugins();

	const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);
	const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
	const [isUninstallModalOpen, setIsUninstallModalOpen] = useState(false);
	const [selectedPlugin, setSelectedPlugin] = useState<PluginSummary | null>(
		null,
	);
	const [pluginInfo, setPluginInfo] = useState<PluginInfo | null>(null);
	const [isLoadingInfo, setIsLoadingInfo] = useState(false);
	const [dropTables, setDropTables] = useState(false);
	const [removePermissions, setRemovePermissions] = useState(false);
	const [deleteFiles, setDeleteFiles] = useState(false);
	const [upgradeMode, setUpgradeMode] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [successMessage, setSuccessMessage] = useState<string | null>(null);
	const [isProcessing, setIsProcessing] = useState<string | null>(null);

	useEffect(() => {
		setBreadcrumb([
			{ label: "Settings", href: "/settings" },
			{ label: "Plugins" },
		]);
	}, [setBreadcrumb]);

	const loadPlugins = useCallback(async () => {
		try {
			await Promise.all([fetchPlugins(), fetchDiscoveredPlugins()]);
		} catch {
			setError("Failed to load plugins");
		}
	}, [fetchPlugins, fetchDiscoveredPlugins]);

	useEffect(() => {
		loadPlugins();
	}, [loadPlugins]);

	const handleInstallDiscoveredPlugin = async (plugin: DiscoveredPlugin) => {
		setIsProcessing(plugin.plugin_id);
		setError(null);
		try {
			const result = await installDiscoveredPlugin(plugin.plugin_id);
			setSuccessMessage(
				`Plugin "${result.plugin_name}" installed successfully`,
			);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to install plugin");
		} finally {
			setIsProcessing(null);
		}
	};

	const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;

		if (!file.name.endsWith(".zip")) {
			setError("Please upload a ZIP file");
			return;
		}

		setIsProcessing("install");
		setError(null);
		try {
			const result = await installPlugin(file, upgradeMode);
			setSuccessMessage(result.message);
			setIsInstallModalOpen(false);
			setUpgradeMode(false);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to install plugin");
		} finally {
			setIsProcessing(null);
			// Reset file input
			e.target.value = "";
		}
	};

	const openUninstallModal = (plugin: PluginSummary) => {
		setSelectedPlugin(plugin);
		setDropTables(false);
		setRemovePermissions(false);
		setDeleteFiles(false);
		setIsUninstallModalOpen(true);
	};

	const handleUninstall = async () => {
		if (!selectedPlugin) return;

		setIsProcessing(selectedPlugin.plugin_id);
		setError(null);
		try {
			// keepFiles is the inverse of deleteFiles (default: keep files)
			await uninstallPlugin(
				selectedPlugin.plugin_id,
				dropTables,
				removePermissions,
				!deleteFiles,
			);
			const message = deleteFiles
				? `Plugin "${selectedPlugin.manifest?.name || selectedPlugin.plugin_id}" uninstalled`
				: `Plugin "${selectedPlugin.manifest?.name || selectedPlugin.plugin_id}" uninstalled (files kept for reinstallation)`;
			setSuccessMessage(message);
			setIsUninstallModalOpen(false);
			setSelectedPlugin(null);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to uninstall plugin",
			);
		} finally {
			setIsProcessing(null);
		}
	};

	const openConfigModal = async (plugin: PluginSummary) => {
		setSelectedPlugin(plugin);
		setIsLoadingInfo(true);
		setIsConfigModalOpen(true);
		setError(null);
		try {
			const { getPluginInfo } = usePlugins.getState();
			const info = await getPluginInfo(plugin.plugin_id);
			setPluginInfo(info);
		} catch {
			setError("Failed to load plugin configuration");
		} finally {
			setIsLoadingInfo(false);
		}
	};

	const closeConfigModal = () => {
		setIsConfigModalOpen(false);
		setSelectedPlugin(null);
		setPluginInfo(null);
	};

	// Clear success message after 5 seconds
	useEffect(() => {
		if (successMessage) {
			const timer = setTimeout(() => setSuccessMessage(null), 5000);
			return () => clearTimeout(timer);
		}
	}, [successMessage]);

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
								No plugins installed. Install a plugin to extend the application
								functionality.
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
												{plugin.manifest?.description ||
													"No description available"}
											</p>
											<div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
												<span>Version: {plugin.plugin_version}</span>
												{plugin.manifest?.author && (
													<span>Author: {plugin.manifest.author}</span>
												)}
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
												<h3 className="font-medium text-gray-900">
													{plugin.name}
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
												{plugin.description}
											</p>
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

			{/* Install Modal */}
			<Modal
				isOpen={isInstallModalOpen}
				onClose={() => {
					setIsInstallModalOpen(false);
					setUpgradeMode(false);
				}}
				title="Install Plugin"
			>
				<div className="space-y-4">
					<p className="text-sm text-gray-600">
						Upload a plugin package (ZIP file) to install a new plugin or to
						upgrade an existing one.
					</p>
					<div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
						<Upload className="h-10 w-10 text-gray-400 mx-auto mb-4" />
						<label
							htmlFor="plugin-upload"
							className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium"
						>
							Choose a file
							<input
								id="plugin-upload"
								type="file"
								accept=".zip"
								onChange={handleFileUpload}
								className="hidden"
								disabled={isProcessing === "install"}
							/>
						</label>
						<p className="text-sm text-gray-500 mt-2">or drag and drop</p>
					</div>
					<label className="flex items-center gap-2">
						<input
							type="checkbox"
							checked={upgradeMode}
							onChange={(e) => setUpgradeMode(e.target.checked)}
							className="rounded border-gray-300"
							disabled={isProcessing === "install"}
						/>
						<span className="text-sm text-gray-700">
							Upgrade existing plugin (replace with new version)
						</span>
					</label>
					{isProcessing === "install" && (
						<div className="flex items-center justify-center gap-2">
							<Spinner className="h-5 w-5" />
							<span className="text-sm text-gray-600">
								{upgradeMode ? "Upgrading plugin..." : "Installing plugin..."}
							</span>
						</div>
					)}
					<div className="flex justify-end">
						<Button
							variant="secondary"
							onClick={() => {
								setIsInstallModalOpen(false);
								setUpgradeMode(false);
							}}
							disabled={isProcessing === "install"}
						>
							Cancel
						</Button>
					</div>
				</div>
			</Modal>

			{/* Config Modal */}
			<Modal
				isOpen={isConfigModalOpen}
				onClose={closeConfigModal}
				title="Plugin Configuration"
				size="lg"
			>
				{isLoadingInfo ? (
					<div className="flex justify-center py-8">
						<Spinner />
					</div>
				) : pluginInfo ? (
					<div className="space-y-6">
						{/* Plugin Info */}
						<div>
							<h3 className="font-medium text-gray-900 mb-2">Information</h3>
							<dl className="grid grid-cols-2 gap-4 text-sm">
								<div>
									<dt className="text-gray-500">ID</dt>
									<dd className="font-mono">{pluginInfo.plugin_id}</dd>
								</div>
								<div>
									<dt className="text-gray-500">Version</dt>
									<dd>{pluginInfo.plugin_version}</dd>
								</div>
								{pluginInfo.migration_version && (
									<div>
										<dt className="text-gray-500">Migration Version</dt>
										<dd className="font-mono text-xs">
											{pluginInfo.migration_version}
										</dd>
									</div>
								)}
							</dl>
						</div>

						{/* Required Permissions */}
						{((pluginInfo.manifest?.required_permissions &&
							pluginInfo.manifest.required_permissions.length > 0) ||
							(pluginInfo.manifest?.permissions &&
								pluginInfo.manifest.permissions.length > 0 &&
								!pluginInfo.manifest?.required_permissions)) && (
							<div>
								<h3 className="font-medium text-gray-900 mb-2">
									Required Permissions
								</h3>
								<p className="text-xs text-gray-500 mb-2">
									Permissions this plugin needs from the host application
								</p>
								<div className="flex flex-wrap gap-2">
									{(
										pluginInfo.manifest.required_permissions ||
										pluginInfo.manifest.permissions
									).map((perm) => (
										<Badge
											key={perm}
											variant="default"
											className="font-mono text-xs"
										>
											{perm}
										</Badge>
									))}
								</div>
							</div>
						)}

						{/* Provided Permissions */}
						{pluginInfo.manifest?.provided_permissions &&
							pluginInfo.manifest.provided_permissions.length > 0 && (
								<div>
									<h3 className="font-medium text-gray-900 mb-2">
										Provided Permissions
									</h3>
									<p className="text-xs text-gray-500 mb-2">
										Custom permissions this plugin adds to the system
									</p>
									<div className="space-y-2">
										{pluginInfo.manifest.provided_permissions.map((perm) => (
											<div
												key={perm.code}
												className="flex items-start gap-2 bg-gray-50 p-2 rounded"
											>
												<Badge
													variant="info"
													className="font-mono text-xs shrink-0"
												>
													{perm.code}
												</Badge>
												{perm.description && (
													<span className="text-xs text-gray-600">
														{perm.description}
													</span>
												)}
											</div>
										))}
									</div>
								</div>
							)}

						{/* Settings */}
						{Object.keys(pluginInfo.settings || {}).length > 0 && (
							<div>
								<h3 className="font-medium text-gray-900 mb-2">Settings</h3>
								<Alert variant="info">
									Plugin settings configuration will be available in a future
									update.
								</Alert>
							</div>
						)}

						{/* Config Schema Info */}
						{Object.keys(pluginInfo.config_schema || {}).length > 0 && (
							<div>
								<h3 className="font-medium text-gray-900 mb-2">
									Configuration Schema
								</h3>
								<pre className="text-xs bg-gray-50 p-3 rounded overflow-auto max-h-48">
									{JSON.stringify(pluginInfo.config_schema, null, 2)}
								</pre>
							</div>
						)}

						<div className="flex justify-end">
							<Button variant="secondary" onClick={closeConfigModal}>
								Close
							</Button>
						</div>
					</div>
				) : (
					<p className="text-gray-500">
						No configuration available for this plugin.
					</p>
				)}
			</Modal>

			{/* Uninstall Confirmation Modal */}
			<Modal
				isOpen={isUninstallModalOpen}
				onClose={() => {
					setIsUninstallModalOpen(false);
					setSelectedPlugin(null);
				}}
				title="Uninstall Plugin"
			>
				<div className="space-y-4">
					<p className="text-gray-600">
						Are you sure you want to uninstall{" "}
						<strong>
							{selectedPlugin?.manifest?.name || selectedPlugin?.plugin_id}
						</strong>
						?
					</p>

					<label className="flex items-center gap-2">
						<input
							type="checkbox"
							checked={dropTables}
							onChange={(e) => setDropTables(e.target.checked)}
							className="rounded border-gray-300"
						/>
						<span className="text-sm text-gray-700">
							Also delete plugin database tables (data will be lost)
						</span>
					</label>

					{/* Only show remove permissions if plugin has provided permissions */}
					{selectedPlugin?.manifest?.provided_permissions &&
						selectedPlugin.manifest.provided_permissions.length > 0 && (
							<label className="flex items-center gap-2">
								<input
									type="checkbox"
									checked={removePermissions}
									onChange={(e) => setRemovePermissions(e.target.checked)}
									className="rounded border-gray-300"
								/>
								<span className="text-sm text-gray-700">
									Also remove plugin-provided permissions from the system
								</span>
							</label>
						)}

					<label className="flex items-center gap-2">
						<input
							type="checkbox"
							checked={deleteFiles}
							onChange={(e) => setDeleteFiles(e.target.checked)}
							className="rounded border-gray-300"
						/>
						<span className="text-sm text-gray-700">
							Also delete plugin files from disk (cannot be reinstalled without
							re-uploading)
						</span>
					</label>

					{(dropTables || removePermissions || deleteFiles) && (
						<Alert variant="warning">
							{buildUninstallWarning(
								dropTables,
								removePermissions,
								deleteFiles,
							)}
						</Alert>
					)}

					<div className="flex justify-end gap-3 pt-4">
						<Button
							variant="secondary"
							onClick={() => {
								setIsUninstallModalOpen(false);
								setSelectedPlugin(null);
							}}
						>
							Cancel
						</Button>
						<Button
							variant="danger"
							onClick={handleUninstall}
							isLoading={isProcessing === selectedPlugin?.plugin_id}
						>
							Uninstall
						</Button>
					</div>
				</div>
			</Modal>
		</div>
	);
}
