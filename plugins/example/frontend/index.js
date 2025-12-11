// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
/**
 * Example Plugin Frontend Module
 *
 * This demonstrates how to create a frontend plugin that integrates
 * with the HomeOffice Assistant application.
 *
 * The plugin exports:
 * - manifest: Plugin metadata
 * - getNavItems(): Returns navigation items for the sidebar
 * - getRoutes(): Returns React routes for the plugin pages
 * - widgets: Optional dashboard widgets
 * - onLoad(): Called when plugin is loaded
 * - onUnload(): Called when plugin is unloaded
 */

// Plugin manifest (should match backend manifest)
export const manifest = {
	id: "example",
	name: "Example Plugin",
	version: "1.0.0",
	description: "A demonstration plugin showing all plugin system capabilities",
};

/**
 * Get navigation items to add to the sidebar.
 * These appear in the plugin section of the navigation.
 */
export function getNavItems() {
	return [
		{
			label: "Example Plugin",
			path: "/plugins/example",
			icon: "FileText", // Lucide icon name
			order: 10,
		},
	];
}

/**
 * Get React routes for this plugin.
 * Routes are automatically prefixed with /plugins/{plugin_id}
 */
export function getRoutes() {
	return [
		{
			path: "/",
			component: ExamplePage,
		},
	];
}

/**
 * Optional widgets that can be embedded in other parts of the app.
 */
export const widgets = {
	// Dashboard widget showing plugin summary
	dashboard: DashboardWidget,
};

/**
 * Called when the plugin is loaded.
 */
export async function onLoad() {
	console.log("[ExamplePlugin] Frontend module loaded");
}

/**
 * Called when the plugin is unloaded.
 */
export async function onUnload() {
	console.log("[ExamplePlugin] Frontend module unloaded");
}

// ============================================================================
// Components (simplified - in production these would be separate files)
// ============================================================================

/**
 * Main example plugin page component.
 * In a real plugin, this would be in a separate file and use proper React imports.
 */
function ExamplePage() {
	// This is a simplified component that works without JSX compilation
	// In production, you would use a proper build process

	const React = window.React;
	const { useState, useEffect } = React;

	const [notes, setNotes] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [newTitle, setNewTitle] = useState("");
	const [newContent, setNewContent] = useState("");

	useEffect(() => {
		fetchNotes();
	}, []);

	async function fetchNotes() {
		try {
			const response = await fetch("/api/v1/plugin/example/notes", {
				credentials: "include",
			});
			if (!response.ok) throw new Error("Failed to fetch notes");
			const data = await response.json();
			setNotes(data);
		} catch (e) {
			setError(e.message);
		} finally {
			setLoading(false);
		}
	}

	async function createNote(e) {
		e.preventDefault();
		if (!newTitle.trim()) return;

		try {
			const response = await fetch("/api/v1/plugin/example/notes", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				credentials: "include",
				body: JSON.stringify({ title: newTitle, content: newContent }),
			});
			if (!response.ok) throw new Error("Failed to create note");
			setNewTitle("");
			setNewContent("");
			fetchNotes();
		} catch (e) {
			setError(e.message);
		}
	}

	async function deleteNote(id) {
		try {
			const response = await fetch(`/api/v1/plugin/example/notes/${id}`, {
				method: "DELETE",
				credentials: "include",
			});
			if (!response.ok) throw new Error("Failed to delete note");
			fetchNotes();
		} catch (e) {
			setError(e.message);
		}
	}

	// Using React.createElement instead of JSX
	const h = React.createElement;

	if (loading) {
		return h("div", { className: "p-6" }, h("p", null, "Loading..."));
	}

	return h(
		"div",
		{ className: "p-6 max-w-4xl mx-auto" },
		// Header
		h("h1", { className: "text-2xl font-bold mb-6" }, "Example Plugin - Notes"),

		// Error message
		error &&
			h(
				"div",
				{ className: "bg-red-100 text-red-700 p-4 rounded mb-4" },
				error,
			),

		// Create note form
		h(
			"form",
			{
				onSubmit: createNote,
				className: "bg-white p-4 rounded-lg shadow mb-6",
			},
			h("h2", { className: "text-lg font-semibold mb-4" }, "Create New Note"),
			h("input", {
				type: "text",
				value: newTitle,
				onChange: (e) => setNewTitle(e.target.value),
				placeholder: "Note title",
				className: "w-full p-2 border rounded mb-2",
			}),
			h("textarea", {
				value: newContent,
				onChange: (e) => setNewContent(e.target.value),
				placeholder: "Note content (optional)",
				className: "w-full p-2 border rounded mb-2",
				rows: 3,
			}),
			h(
				"button",
				{
					type: "submit",
					className:
						"bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700",
				},
				"Create Note",
			),
		),

		// Notes list
		h(
			"div",
			{ className: "space-y-4" },
			notes.length === 0
				? h(
						"p",
						{ className: "text-gray-500" },
						"No notes yet. Create one above!",
					)
				: notes.map((note) =>
						h(
							"div",
							{ key: note.id, className: "bg-white p-4 rounded-lg shadow" },
							h(
								"div",
								{ className: "flex justify-between items-start" },
								h("h3", { className: "font-semibold" }, note.title),
								h(
									"button",
									{
										onClick: () => deleteNote(note.id),
										className: "text-red-600 hover:text-red-800",
									},
									"Delete",
								),
							),
							note.content &&
								h("p", { className: "text-gray-600 mt-2" }, note.content),
							h(
								"p",
								{ className: "text-sm text-gray-400 mt-2" },
								`Created: ${new Date(note.created_at).toLocaleString()}`,
							),
						),
					),
		),
	);
}

/**
 * Dashboard widget showing plugin stats.
 */
function DashboardWidget() {
	const React = window.React;
	const { useState, useEffect } = React;
	const h = React.createElement;

	const [info, setInfo] = useState(null);

	useEffect(() => {
		fetch("/api/v1/plugin/example/info", { credentials: "include" })
			.then((r) => r.json())
			.then(setInfo)
			.catch(console.error);
	}, []);

	if (!info) return null;

	return h(
		"div",
		{ className: "bg-white p-4 rounded-lg shadow" },
		h("h3", { className: "font-semibold mb-2" }, "Example Plugin"),
		h("p", { className: "text-gray-600" }, info.greeting),
		h(
			"p",
			{ className: "text-sm text-gray-500 mt-2" },
			`${info.note_count} notes`,
		),
	);
}
