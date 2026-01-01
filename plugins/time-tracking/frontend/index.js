// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
/**
 * Time Tracking Plugin Frontend Module
 *
 * Track working hours with Austrian labor law compliance.
 */

// Plugin manifest
export const manifest = {
	id: "time-tracking",
	name: "Time Tracking",
	version: "1.0.0",
	description: "Track working hours with Austrian labor law compliance",
}

/**
 * Get navigation items for the sidebar.
 */
export function getNavItems() {
	return [
		{
			label: "Time Tracking",
			path: "/plugins/time-tracking",
			icon: "Clock",
			order: 25,
		},
	]
}

/**
 * Get React routes for this plugin.
 */
export function getRoutes() {
	return [
		{
			path: "/",
			component: TimeTrackingPage,
		},
	]
}

/**
 * Widget for company detail page.
 */
export const widgets = {
	companyDetail: CompanyTimeSettingsWidget,
}

export async function onLoad() {
	console.log("[TimeTracking] Frontend module loaded")
}

export async function onUnload() {
	console.log("[TimeTracking] Frontend module unloaded")
}

// ============================================================================
// API Functions
// ============================================================================

async function apiGet(path) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		credentials: "include",
	})
	if (!response.ok) {
		const error = await response.json().catch(() => ({}))
		throw new Error(error.detail || `Request failed: ${response.status}`)
	}
	return response.json()
}

async function apiPost(path, data) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		credentials: "include",
		body: JSON.stringify(data),
	})
	if (!response.ok) {
		const error = await response.json().catch(() => ({}))
		throw new Error(error.detail || `Request failed: ${response.status}`)
	}
	return response.json()
}

async function apiPut(path, data) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "PUT",
		headers: { "Content-Type": "application/json" },
		credentials: "include",
		body: JSON.stringify(data),
	})
	if (!response.ok) {
		const error = await response.json().catch(() => ({}))
		throw new Error(error.detail || `Request failed: ${response.status}`)
	}
	return response.json()
}

async function apiDelete(path) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "DELETE",
		credentials: "include",
	})
	if (!response.ok) {
		const error = await response.json().catch(() => ({}))
		throw new Error(error.detail || `Request failed: ${response.status}`)
	}
	return response.status === 204 ? null : response.json()
}

// ============================================================================
// Date/Time Formatting Helpers
// ============================================================================

/**
 * Format a date string using user's locale with leading zeros.
 * @param {string} dateStr - ISO date string (YYYY-MM-DD)
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
	const date = new Date(dateStr)
	return date.toLocaleDateString(undefined, {
		day: "2-digit",
		month: "2-digit",
		year: "numeric",
	})
}

/**
 * Format a time string for display.
 * @param {string|null} timeStr - Time string (HH:MM:SS or HH:MM)
 * @returns {string} Formatted time or "-"
 */
function formatTime(timeStr) {
	if (!timeStr) return "-"
	// Return just HH:MM portion
	return timeStr.substring(0, 5)
}

/**
 * Get the short day name for a date.
 * @param {string} dateStr - ISO date string
 * @returns {string} Short day name (Mon, Tue, etc.)
 */
function getDayName(dateStr) {
	const date = new Date(dateStr)
	return date.toLocaleDateString(undefined, { weekday: "short" })
}

// ============================================================================
// Day Type Helpers
// ============================================================================

const DAY_TYPE_LABELS = {
	work: "Work",
	vacation: "Vacation",
	sick: "Sick",
	doctor_visit: "Doctor",
	public_holiday: "Holiday",
	comp_time: "Comp Time",
	unpaid_leave: "Unpaid",
	weekend: "Weekend",
}

const DAY_TYPE_COLORS = {
	work: "bg-green-100 text-green-800",
	vacation: "bg-blue-100 text-blue-800",
	sick: "bg-red-100 text-red-800",
	doctor_visit: "bg-orange-100 text-orange-800",
	public_holiday: "bg-purple-100 text-purple-800",
	comp_time: "bg-yellow-100 text-yellow-800",
	unpaid_leave: "bg-gray-100 text-gray-800",
	weekend: "bg-gray-50 text-gray-500",
}

// ============================================================================
// Main Time Tracking Page
// ============================================================================

const WORK_LOCATIONS = {
	office: "Office",
	remote: "Remote/Home",
	client_site: "Client Site",
	travel: "Travel",
}

function TimeTrackingPage() {
	const React = window.React
	const { useState, useEffect } = React
	const h = React.createElement

	const [todayRecord, setTodayRecord] = useState(null)
	const [weekRecords, setWeekRecords] = useState([])
	const [balance, setBalance] = useState(null)
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const [companies, setCompanies] = useState([])
	const [selectedCompanyId, setSelectedCompanyId] = useState(null)
	const [showAddModal, setShowAddModal] = useState(false)
	const [editingRecord, setEditingRecord] = useState(null)
	const [showLeaveBalance, setShowLeaveBalance] = useState(false)
	const [formData, setFormData] = useState({
		date: new Date().toISOString().split("T")[0],
		day_type: "work",
		check_in: "09:00",
		check_out: "17:00",
		work_location: "remote",
		notes: "",
	})

	// Helper to get company name from ID
	const getCompanyName = (id) => companies.find((c) => c.id === id)?.name || "-"

	// Calculate week stats
	const weekWorkDays = weekRecords.filter((r) => r.day_type === "work").length
	const weekTotalHours = weekRecords.reduce((sum, r) => sum + (r.net_hours || 0), 0)
	const weekOvertime = Math.max(0, weekTotalHours - 40)

	// Fetch companies on mount
	useEffect(() => {
		fetch("/api/v1/companies", { credentials: "include" })
			.then((r) => r.json())
			.then((data) => {
				setCompanies(data)
				if (data.length > 0) {
					setSelectedCompanyId(data[0].id)
				}
			})
			.catch(console.error)
	}, [])

	// Fetch data when company changes
	useEffect(() => {
		if (!selectedCompanyId) return
		fetchData()
	}, [selectedCompanyId])

	async function fetchData() {
		setLoading(true)
		setError(null)
		try {
			// Get today's record
			const today = await apiGet("/today").catch(() => null)
			setTodayRecord(today)

			// Get week records
			const now = new Date()
			const weekStart = new Date(now)
			weekStart.setDate(now.getDate() - now.getDay() + 1) // Monday
			const weekEnd = new Date(weekStart)
			weekEnd.setDate(weekStart.getDate() + 6)

			const fromDate = weekStart.toISOString().split("T")[0]
			const toDate = weekEnd.toISOString().split("T")[0]
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			)
			setWeekRecords(records)

			// Get leave balance
			const year = now.getFullYear()
			const bal = await apiGet(
				`/leave-balance?year=${year}&company_id=${selectedCompanyId}`,
			)
			setBalance(bal)
		} catch (e) {
			setError(e.message)
		} finally {
			setLoading(false)
		}
	}

	async function handleCheckIn() {
		try {
			const data = {
				company_id: selectedCompanyId,
				work_location: "remote",
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			}
			await apiPost("/check-in", data)
			fetchData()
		} catch (e) {
			setError(e.message)
		}
	}

	async function handleCheckOut() {
		try {
			const data = {
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			}
			await apiPost("/check-out", data)
			fetchData()
		} catch (e) {
			setError(e.message)
		}
	}

	async function handleSaveEntry(e) {
		e.preventDefault()
		setError(null)
		try {
			const data = {
				date: formData.date,
				day_type: formData.day_type,
				company_id: selectedCompanyId,
				work_location: formData.day_type === "work" ? formData.work_location : null,
				notes: formData.notes || null,
			}
			// Only add times for work days
			if (formData.day_type === "work" && formData.check_in) {
				data.check_in = formData.check_in + ":00"
			}
			if (formData.day_type === "work" && formData.check_out) {
				data.check_out = formData.check_out + ":00"
			}

			if (editingRecord) {
				await apiPut(`/records/${editingRecord.id}`, data)
			} else {
				await apiPost("/records", data)
			}

			closeModal()
			fetchData()
		} catch (e) {
			setError(e.message)
		}
	}

	function openEditModal(record) {
		setEditingRecord(record)
		setFormData({
			date: record.date,
			day_type: record.day_type,
			check_in: record.check_in ? record.check_in.substring(0, 5) : "09:00",
			check_out: record.check_out ? record.check_out.substring(0, 5) : "17:00",
			work_location: record.work_location || "remote",
			notes: record.notes || "",
		})
		setShowAddModal(true)
	}

	function closeModal() {
		setShowAddModal(false)
		setEditingRecord(null)
		setFormData({
			date: new Date().toISOString().split("T")[0],
			day_type: "work",
			check_in: "09:00",
			check_out: "17:00",
			work_location: "remote",
			notes: "",
		})
	}

	async function handleDeleteRecord(recordId) {
		if (!confirm("Are you sure you want to delete this time entry?")) {
			return
		}
		try {
			await apiDelete(`/records/${recordId}`)
			fetchData()
		} catch (e) {
			setError(e.message)
		}
	}

	if (loading) {
		return h(
			"div",
			{ className: "p-6" },
			h("p", { className: "text-gray-500" }, "Loading..."),
		)
	}

	return h(
		"div",
		{ className: "p-6 max-w-6xl mx-auto" },

		// Header with company selector and Add Entry button
		h(
			"div",
			{ className: "flex justify-between items-center mb-6" },
			h("h1", { className: "text-2xl font-bold" }, "Time Tracking"),
			h(
				"div",
				{ className: "flex gap-3 items-center" },
				h(
					"button",
					{
						onClick: () => setShowAddModal(true),
						className: "bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700",
					},
					"Add Entry",
				),
				h(
					"select",
					{
						value: selectedCompanyId || "",
						onChange: (e) => setSelectedCompanyId(e.target.value),
						className: "border rounded px-3 py-2",
					},
					companies.map((c) => h("option", { key: c.id, value: c.id }, c.name)),
				),
			),
		),

		// Error message
		error &&
			h(
				"div",
				{ className: "bg-red-100 text-red-700 p-4 rounded mb-4" },
				error,
			),

		// Compact stats row (Today + This Week merged)
		h(
			"div",
			{ className: "flex items-center justify-between bg-gray-50 rounded-lg p-4 mb-6" },
			h(
				"div",
				{ className: "flex items-center gap-6" },
				// Today status
				h(
					"div",
					{ className: "flex items-center gap-3" },
					h("div", {
						className: `w-3 h-3 rounded-full ${todayRecord && !todayRecord.check_out ? "bg-green-500" : "bg-gray-300"}`,
					}),
					h(
						"div",
						null,
						h("span", { className: "text-sm text-gray-500" }, "Today"),
						todayRecord
							? h(
									"p",
									{ className: "font-medium" },
									`${formatTime(todayRecord.check_in)} - ${todayRecord.check_out ? formatTime(todayRecord.check_out) : "ongoing"}`,
									todayRecord.net_hours &&
										h("span", { className: "text-gray-400 ml-1" }, `(${todayRecord.net_hours.toFixed(1)}h)`),
								)
							: h("p", { className: "text-gray-500" }, "Not checked in"),
					),
				),
				h("div", { className: "w-px h-10 bg-gray-300" }),
				// This Week summary
				h(
					"div",
					{ className: "flex gap-6 text-sm" },
					h(
						"div",
						null,
						h("span", { className: "text-gray-500" }, "Work Days"),
						h("p", { className: "font-semibold text-gray-900" }, weekWorkDays),
					),
					h(
						"div",
						null,
						h("span", { className: "text-gray-500" }, "Total Hours"),
						h("p", { className: "font-semibold text-gray-900" }, `${weekTotalHours.toFixed(1)}h`),
					),
					weekOvertime > 0 &&
						h(
							"div",
							null,
							h("span", { className: "text-gray-500" }, "Overtime"),
							h("p", { className: "font-semibold text-amber-600" }, `+${weekOvertime.toFixed(1)}h`),
						),
				),
			),
			// Quick action button
			todayRecord && !todayRecord.check_out
				? h(
						"button",
						{
							onClick: handleCheckOut,
							className: "text-sm text-red-600 hover:text-red-700 font-medium",
						},
						"Check Out",
					)
				: !todayRecord &&
					h(
						"button",
						{
							onClick: handleCheckIn,
							className: "text-sm text-green-600 hover:text-green-700 font-medium",
						},
						"Check In",
					),
		),

		// Week view table
		h(
			"div",
			{ className: "bg-white rounded-lg shadow overflow-hidden mb-6" },
			h(
				"table",
				{ className: "w-full" },
				h(
					"thead",
					{ className: "bg-gray-50" },
					h(
						"tr",
						null,
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Date"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Day"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Company"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Type"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Check In"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Check Out"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Break"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Net"),
						h("th", { className: "px-4 py-3 text-left text-sm font-medium text-gray-500" }, "Actions"),
					),
				),
				h(
					"tbody",
					null,
					weekRecords.length === 0
						? h(
								"tr",
								null,
								h(
									"td",
									{ colSpan: 9, className: "px-4 py-8 text-center text-gray-500" },
									"No records this week",
								),
							)
						: weekRecords.map((record, i) =>
								h(
									"tr",
									{
										key: record.id,
										className: `${i % 2 === 0 ? "bg-white" : "bg-gray-50"} ${record.is_locked ? "opacity-60" : ""}`,
									},
									h("td", { className: "px-4 py-3" }, formatDate(record.date)),
									h("td", { className: "px-4 py-3" }, getDayName(record.date)),
									h("td", { className: "px-4 py-3 text-gray-600" }, getCompanyName(record.company_id)),
									h(
										"td",
										{ className: "px-4 py-3" },
										h(
											"span",
											{
												className: `px-2 py-1 rounded text-xs ${DAY_TYPE_COLORS[record.day_type] || "bg-gray-100"}`,
											},
											DAY_TYPE_LABELS[record.day_type] || record.day_type,
										),
									),
									h("td", { className: "px-4 py-3" }, formatTime(record.check_in)),
									h("td", { className: "px-4 py-3" }, formatTime(record.check_out)),
									h("td", { className: "px-4 py-3" }, record.break_minutes ? `${record.break_minutes}m` : "-"),
									h("td", { className: "px-4 py-3 font-medium" }, record.net_hours ? `${record.net_hours.toFixed(1)}h` : "-"),
									h(
										"td",
										{ className: "px-4 py-3" },
										record.is_locked
											? h("span", { className: "px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs" }, "Locked")
											: h(
													"div",
													{ className: "flex gap-2" },
													h(
														"button",
														{
															onClick: () => openEditModal(record),
															className: "text-gray-400 hover:text-blue-600 text-sm",
														},
														"Edit",
													),
													h(
														"button",
														{
															onClick: () => handleDeleteRecord(record.id),
															className: "text-gray-400 hover:text-red-600 text-sm",
														},
														"Delete",
													),
												),
									),
								),
							),
				),
			),
		),

		// Leave Balance (Collapsible)
		balance &&
			h(
				"details",
				{
					className: "bg-gray-50 rounded-lg",
					open: showLeaveBalance,
					onToggle: (e) => setShowLeaveBalance(e.target.open),
				},
				h(
					"summary",
					{ className: "px-4 py-3 cursor-pointer font-medium text-gray-700 hover:bg-gray-100 rounded-lg" },
					`Leave Balance (${balance.vacation_remaining} vacation days, ${balance.comp_time_balance?.toFixed(1) || 0}h comp time)`,
				),
				h(
					"div",
					{ className: "px-4 pb-4 grid grid-cols-3 gap-4" },
					h(
						"div",
						{ className: "bg-white p-4 rounded-lg border" },
						h("p", { className: "text-sm text-gray-500" }, "Vacation Days"),
						h("p", { className: "text-2xl font-bold text-green-600" }, balance.vacation_remaining),
					),
					h(
						"div",
						{ className: "bg-white p-4 rounded-lg border" },
						h("p", { className: "text-sm text-gray-500" }, "Comp Time"),
						h("p", { className: "text-2xl font-bold text-blue-600" }, `${balance.comp_time_balance?.toFixed(1) || 0}h`),
					),
					h(
						"div",
						{ className: "bg-white p-4 rounded-lg border" },
						h("p", { className: "text-sm text-gray-500" }, "Sick Days Used"),
						h("p", { className: "text-2xl font-bold text-gray-600" }, balance.sick_days_taken),
					),
				),
			),

		// Add/Edit Entry Modal
		showAddModal &&
			h(
				"div",
				{
					className: "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50",
					onClick: (e) => {
						if (e.target === e.currentTarget) closeModal()
					},
				},
				h(
					"div",
					{ className: "bg-white rounded-lg shadow-xl p-6 w-full max-w-md" },
					h("h2", { className: "text-xl font-bold mb-4" }, editingRecord ? "Edit Time Entry" : "Add Time Entry"),
					h(
						"form",
						{ onSubmit: handleSaveEntry },
						// Date
						h(
							"div",
							{ className: "mb-4" },
							h("label", { className: "block text-sm font-medium mb-1" }, "Date"),
							h("input", {
								type: "date",
								value: formData.date,
								onChange: (e) => setFormData({ ...formData, date: e.target.value }),
								className: "w-full border rounded px-3 py-2",
								required: true,
							}),
						),
						// Day Type
						h(
							"div",
							{ className: "mb-4" },
							h("label", { className: "block text-sm font-medium mb-1" }, "Type"),
							h(
								"select",
								{
									value: formData.day_type,
									onChange: (e) => setFormData({ ...formData, day_type: e.target.value }),
									className: "w-full border rounded px-3 py-2",
								},
								Object.entries(DAY_TYPE_LABELS).map(([value, label]) =>
									h("option", { key: value, value }, label),
								),
							),
						),
						// Work-specific fields
						formData.day_type === "work" &&
							h(
								"div",
								null,
								// Check In Time
								h(
									"div",
									{ className: "mb-4" },
									h("label", { className: "block text-sm font-medium mb-1" }, "Check In"),
									h("input", {
										type: "time",
										value: formData.check_in,
										onChange: (e) => setFormData({ ...formData, check_in: e.target.value }),
										className: "w-full border rounded px-3 py-2",
									}),
								),
								// Check Out Time
								h(
									"div",
									{ className: "mb-4" },
									h("label", { className: "block text-sm font-medium mb-1" }, "Check Out"),
									h("input", {
										type: "time",
										value: formData.check_out,
										onChange: (e) => setFormData({ ...formData, check_out: e.target.value }),
										className: "w-full border rounded px-3 py-2",
									}),
								),
								// Work Location
								h(
									"div",
									{ className: "mb-4" },
									h("label", { className: "block text-sm font-medium mb-1" }, "Location"),
									h(
										"select",
										{
											value: formData.work_location,
											onChange: (e) => setFormData({ ...formData, work_location: e.target.value }),
											className: "w-full border rounded px-3 py-2",
										},
										Object.entries(WORK_LOCATIONS).map(([value, label]) =>
											h("option", { key: value, value }, label),
										),
									),
								),
							),
						// Notes
						h(
							"div",
							{ className: "mb-4" },
							h("label", { className: "block text-sm font-medium mb-1" }, "Notes"),
							h("textarea", {
								value: formData.notes,
								onChange: (e) => setFormData({ ...formData, notes: e.target.value }),
								className: "w-full border rounded px-3 py-2",
								rows: 2,
								placeholder: "Optional notes...",
							}),
						),
						// Buttons
						h(
							"div",
							{ className: "flex justify-end gap-3" },
							h(
								"button",
								{
									type: "button",
									onClick: closeModal,
									className: "px-4 py-2 border rounded hover:bg-gray-100",
								},
								"Cancel",
							),
							h(
								"button",
								{
									type: "submit",
									className: "px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700",
								},
								editingRecord ? "Update" : "Save",
							),
						),
					),
				),
			),
	)
}

// ============================================================================
// Company Time Settings Widget (for company detail page injection)
// ============================================================================

function CompanyTimeSettingsWidget({ companyId }) {
	const React = window.React
	const { useState, useEffect } = React
	const h = React.createElement

	const [settings, setSettings] = useState(null)
	const [loading, setLoading] = useState(true)

	useEffect(() => {
		if (!companyId) return
		apiGet(`/settings/company/${companyId}`)
			.then(setSettings)
			.catch(console.error)
			.finally(() => setLoading(false))
	}, [companyId])

	if (loading) {
		return h(
			"div",
			{ className: "p-4 text-gray-500" },
			"Loading time settings...",
		)
	}

	if (!settings) {
		return null
	}

	return h(
		"div",
		{ className: "bg-white p-4 rounded-lg shadow" },
		h("h3", { className: "font-semibold mb-3" }, "Time Tracking Settings"),
		h(
			"div",
			{ className: "grid grid-cols-2 gap-4 text-sm" },
			h(
				"div",
				null,
				h("span", { className: "text-gray-500" }, "Vacation Days/Year: "),
				h("span", { className: "font-medium" }, settings.vacation_days_per_year),
			),
			h(
				"div",
				null,
				h("span", { className: "text-gray-500" }, "Daily OT Threshold: "),
				h(
					"span",
					{ className: "font-medium" },
					`${settings.daily_overtime_threshold}h`,
				),
			),
			h(
				"div",
				null,
				h("span", { className: "text-gray-500" }, "Weekly OT Threshold: "),
				h(
					"span",
					{ className: "font-medium" },
					`${settings.weekly_overtime_threshold}h`,
				),
			),
			h(
				"div",
				null,
				h("span", { className: "text-gray-500" }, "Lock Period: "),
				h(
					"span",
					{ className: "font-medium" },
					`${settings.lock_period_days} days`,
				),
			),
		),
	)
}

// Default export for the plugin loader
export default {
	manifest,
	getNavItems,
	getRoutes,
	widgets,
	onLoad,
	onUnload,
}
