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
	// Phase 2: Submission state
	const [submissions, setSubmissions] = useState([])
	const [selectedMonth, setSelectedMonth] = useState(() => {
		const now = new Date()
		return { year: now.getFullYear(), month: now.getMonth() + 1 }
	})
	const [showSubmissionModal, setShowSubmissionModal] = useState(false)
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [recipientEmail, setRecipientEmail] = useState("")
	const [submissionNotes, setSubmissionNotes] = useState("")
	const [monthRecords, setMonthRecords] = useState([])
	// Phase 3: Calendar view state
	const [viewMode, setViewMode] = useState("calendar") // 'table' or 'calendar'
	const [calendarMonth, setCalendarMonth] = useState(() => {
		const now = new Date()
		return { year: now.getFullYear(), month: now.getMonth() + 1 }
	})
	const [selectedDay, setSelectedDay] = useState(null)
	const [calendarRecords, setCalendarRecords] = useState([])
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

	// Generate last 12 months for dropdown
	const getLastMonths = () => {
		const months = []
		const now = new Date()
		for (let i = 0; i < 12; i++) {
			const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
			months.push({ year: d.getFullYear(), month: d.getMonth() + 1 })
		}
		return months
	}

	// Format month for display
	const formatMonth = (year, month) => {
		const d = new Date(year, month - 1, 1)
		return d.toLocaleDateString(undefined, { year: "numeric", month: "long" })
	}

	// Check if a month has been submitted
	const isMonthSubmitted = (year, month) => {
		return submissions.some((s) => {
			const start = new Date(s.period_start)
			return start.getFullYear() === year && start.getMonth() + 1 === month
		})
	}

	// Calculate month stats from monthRecords
	const monthWorkDays = monthRecords.filter((r) => r.day_type === "work").length
	const monthTotalHours = monthRecords.reduce((sum, r) => sum + (r.net_hours || 0), 0)
	const monthOvertime = Math.max(0, monthTotalHours - monthWorkDays * 8)

	// Calendar helper functions
	const getCalendarDays = (year, month) => {
		const days = []
		const firstDay = new Date(year, month - 1, 1)
		const lastDay = new Date(year, month, 0)

		// Adjust for Monday start (European week)
		let startOffset = firstDay.getDay() - 1
		if (startOffset < 0) startOffset = 6

		// Add previous month days
		const prevMonth = month === 1 ? 12 : month - 1
		const prevYear = month === 1 ? year - 1 : year
		const prevMonthLastDay = new Date(prevYear, prevMonth, 0).getDate()
		for (let i = startOffset - 1; i >= 0; i--) {
			days.push({
				day: prevMonthLastDay - i,
				month: prevMonth,
				year: prevYear,
				isCurrentMonth: false,
			})
		}

		// Add current month days
		for (let d = 1; d <= lastDay.getDate(); d++) {
			days.push({ day: d, month, year, isCurrentMonth: true })
		}

		// Add next month days to fill 6 rows (42 cells)
		const nextMonth = month === 12 ? 1 : month + 1
		const nextYear = month === 12 ? year + 1 : year
		let nextDay = 1
		while (days.length < 42) {
			days.push({
				day: nextDay++,
				month: nextMonth,
				year: nextYear,
				isCurrentMonth: false,
			})
		}

		return days
	}

	const getRecordForDate = (year, month, day) => {
		const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
		return calendarRecords.find((r) => r.date === dateStr)
	}

	const isToday = (year, month, day) => {
		const today = new Date()
		return today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === day
	}

	const isWeekend = (year, month, day) => {
		const d = new Date(year, month - 1, day)
		return d.getDay() === 0 || d.getDay() === 6
	}

	const navigateMonth = (direction) => {
		setCalendarMonth((prev) => {
			let newMonth = prev.month + direction
			let newYear = prev.year
			if (newMonth < 1) {
				newMonth = 12
				newYear--
			} else if (newMonth > 12) {
				newMonth = 1
				newYear++
			}
			return { year: newYear, month: newMonth }
		})
		setSelectedDay(null)
	}

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
		fetchSubmissions()
	}, [selectedCompanyId])

	// Fetch month records when selectedMonth changes
	useEffect(() => {
		if (!selectedCompanyId) return
		fetchMonthRecords()
	}, [selectedCompanyId, selectedMonth])

	// Fetch calendar month records when calendarMonth changes
	useEffect(() => {
		if (!selectedCompanyId) return
		fetchCalendarRecords()
	}, [selectedCompanyId, calendarMonth])

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

	async function fetchSubmissions() {
		try {
			const data = await apiGet(`/submissions?company_id=${selectedCompanyId}`)
			setSubmissions(data.submissions || [])
		} catch (e) {
			console.error("Failed to fetch submissions:", e)
		}
	}

	async function fetchMonthRecords() {
		try {
			const { year, month } = selectedMonth
			const lastDay = new Date(year, month, 0).getDate()
			const fromDate = `${year}-${String(month).padStart(2, "0")}-01`
			const toDate = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			)
			setMonthRecords(records)
		} catch (e) {
			console.error("Failed to fetch month records:", e)
		}
	}

	async function fetchCalendarRecords() {
		try {
			const { year, month } = calendarMonth
			const lastDay = new Date(year, month, 0).getDate()
			const fromDate = `${year}-${String(month).padStart(2, "0")}-01`
			const toDate = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			)
			setCalendarRecords(records)
		} catch (e) {
			console.error("Failed to fetch calendar records:", e)
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

	async function handleSubmitMonth() {
		if (!recipientEmail) {
			setError("Please enter a recipient email address")
			return
		}
		setIsSubmitting(true)
		setError(null)
		try {
			const { year, month } = selectedMonth
			let url = `/submissions?year=${year}&month=${month}&company_id=${selectedCompanyId}&recipient_email=${encodeURIComponent(recipientEmail)}`
			if (submissionNotes) {
				url += `&notes=${encodeURIComponent(submissionNotes)}`
			}
			await apiPost(url, {})
			setShowSubmissionModal(false)
			setRecipientEmail("")
			setSubmissionNotes("")
			fetchSubmissions()
			fetchMonthRecords()
			fetchData() // Refresh week records to show locked status
		} catch (e) {
			setError(e.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	function openSubmissionModal() {
		setRecipientEmail("")
		setSubmissionNotes("")
		setShowSubmissionModal(true)
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

		// View toggle
		h(
			"div",
			{ className: "flex items-center justify-between mb-4" },
			h(
				"div",
				{ className: "flex gap-2" },
				h(
					"button",
					{
						onClick: () => setViewMode("calendar"),
						className: `px-3 py-1.5 rounded text-sm font-medium ${viewMode === "calendar" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`,
					},
					"Calendar",
				),
				h(
					"button",
					{
						onClick: () => setViewMode("table"),
						className: `px-3 py-1.5 rounded text-sm font-medium ${viewMode === "table" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`,
					},
					"Table",
				),
			),
			viewMode === "calendar" &&
				h(
					"div",
					{ className: "flex items-center gap-3" },
					h(
						"button",
						{
							onClick: () => navigateMonth(-1),
							className: "px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded",
						},
						"<",
					),
					h("span", { className: "font-medium min-w-32 text-center" }, formatMonth(calendarMonth.year, calendarMonth.month)),
					h(
						"button",
						{
							onClick: () => navigateMonth(1),
							className: "px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded",
						},
						">",
					),
				),
		),

		// Calendar view
		viewMode === "calendar" &&
			h(
				"div",
				{ className: "bg-white rounded-lg shadow mb-6" },
				// Day headers
				h(
					"div",
					{ className: "grid grid-cols-7 border-b" },
					["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) =>
						h("div", { key: day, className: "px-2 py-2 text-center text-xs font-medium text-gray-500" }, day),
					),
				),
				// Calendar grid
				h(
					"div",
					{ className: "grid grid-cols-7" },
					getCalendarDays(calendarMonth.year, calendarMonth.month).map((cell, idx) => {
						const record = cell.isCurrentMonth ? getRecordForDate(cell.year, cell.month, cell.day) : null
						const isTodayCell = isToday(cell.year, cell.month, cell.day)
						const isWeekendDay = isWeekend(cell.year, cell.month, cell.day)
						const isSelected = selectedDay && selectedDay.year === cell.year && selectedDay.month === cell.month && selectedDay.day === cell.day

						return h(
							"div",
							{
								key: idx,
								onClick: () => cell.isCurrentMonth && setSelectedDay(cell),
								className: `min-h-20 p-2 border-b border-r cursor-pointer transition-colors ${
									!cell.isCurrentMonth ? "bg-gray-50 text-gray-400" : isWeekendDay ? "bg-gray-50" : "bg-white hover:bg-blue-50"
								} ${isSelected ? "ring-2 ring-blue-500 ring-inset" : ""}`,
							},
							// Day number
							h(
								"div",
								{
									className: `text-sm font-medium ${isTodayCell ? "bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center" : ""}`,
								},
								cell.day,
							),
							// Record indicator
							record &&
								h(
									"div",
									{ className: "mt-1" },
									h(
										"span",
										{
											className: `text-xs px-1.5 py-0.5 rounded ${DAY_TYPE_COLORS[record.day_type] || "bg-gray-100"}`,
										},
										DAY_TYPE_LABELS[record.day_type]?.substring(0, 4) || record.day_type.substring(0, 4),
									),
									record.net_hours &&
										h("div", { className: "text-xs text-gray-600 mt-0.5" }, `${record.net_hours.toFixed(1)}h`),
								),
						)
					}),
				),
			),

		// Day detail panel (when a day is selected)
		selectedDay &&
			viewMode === "calendar" &&
			h(
				"div",
				{ className: "bg-white rounded-lg shadow p-4 mb-6" },
				h(
					"div",
					{ className: "flex justify-between items-start mb-3" },
					h(
						"div",
						null,
						h(
							"h3",
							{ className: "font-semibold text-lg" },
							formatDate(`${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`),
						),
						h("p", { className: "text-sm text-gray-500" }, getDayName(`${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`)),
					),
					h(
						"button",
						{
							onClick: () => setSelectedDay(null),
							className: "text-gray-400 hover:text-gray-600",
						},
						"Close",
					),
				),
				(() => {
					const dayRecord = getRecordForDate(selectedDay.year, selectedDay.month, selectedDay.day)
					if (!dayRecord) {
						return h(
							"div",
							{ className: "text-gray-500 text-center py-4" },
							"No record for this day. ",
							h(
								"button",
								{
									onClick: () => {
										setFormData({
											...formData,
											date: `${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`,
										})
										setShowAddModal(true)
									},
									className: "text-blue-600 hover:underline",
								},
								"Add entry",
							),
						)
					}
					return h(
						"div",
						null,
						h(
							"div",
							{ className: "flex items-center gap-2 mb-3" },
							h("span", { className: `px-2 py-1 rounded text-sm ${DAY_TYPE_COLORS[dayRecord.day_type] || "bg-gray-100"}` }, DAY_TYPE_LABELS[dayRecord.day_type] || dayRecord.day_type),
							dayRecord.is_locked && h("span", { className: "px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs" }, "Locked"),
						),
						dayRecord.day_type === "work" &&
							h(
								"div",
								{ className: "grid grid-cols-4 gap-4 text-sm mb-3" },
								h("div", null, h("span", { className: "text-gray-500" }, "Check In: "), formatTime(dayRecord.check_in)),
								h("div", null, h("span", { className: "text-gray-500" }, "Check Out: "), formatTime(dayRecord.check_out)),
								h("div", null, h("span", { className: "text-gray-500" }, "Break: "), dayRecord.break_minutes ? `${dayRecord.break_minutes}m` : "-"),
								h("div", null, h("span", { className: "text-gray-500" }, "Net: "), dayRecord.net_hours ? `${dayRecord.net_hours.toFixed(1)}h` : "-"),
							),
						dayRecord.notes && h("p", { className: "text-sm text-gray-600 mb-3" }, dayRecord.notes),
						!dayRecord.is_locked &&
							h(
								"div",
								{ className: "flex gap-2" },
								h(
									"button",
									{
										onClick: () => openEditModal(dayRecord),
										className: "text-sm text-blue-600 hover:underline",
									},
									"Edit",
								),
								h(
									"button",
									{
										onClick: () => handleDeleteRecord(dayRecord.id),
										className: "text-sm text-red-600 hover:underline",
									},
									"Delete",
								),
							),
					)
				})(),
			),

		// Week view table (hidden when calendar view is active)
		viewMode === "table" &&
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

		// Leave Balance (Collapsible) - moved above Monthly Submission
		balance &&
			h(
				"details",
				{
					className: "bg-gray-50 rounded-lg mb-4",
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
						{ className: "bg-white p-3 rounded-lg border" },
						h("p", { className: "text-xs text-gray-500" }, "Vacation Days"),
						h("p", { className: "text-lg font-bold text-green-600" }, balance.vacation_remaining),
					),
					h(
						"div",
						{ className: "bg-white p-3 rounded-lg border" },
						h("p", { className: "text-xs text-gray-500" }, "Comp Time"),
						h("p", { className: "text-lg font-bold text-blue-600" }, `${balance.comp_time_balance?.toFixed(1) || 0}h`),
					),
					h(
						"div",
						{ className: "bg-white p-3 rounded-lg border" },
						h("p", { className: "text-xs text-gray-500" }, "Sick Days Used"),
						h("p", { className: "text-lg font-bold text-gray-600" }, balance.sick_days_taken),
					),
				),
			),

		// Monthly Submission Section - more compact
		h(
			"div",
			{ className: "bg-white rounded-lg shadow p-4 mb-4" },
			// Header row with stats inline
			h(
				"div",
				{ className: "flex items-center justify-between" },
				h(
					"div",
					{ className: "flex items-center gap-6" },
					h("h2", { className: "text-sm font-semibold text-gray-700" }, "Monthly Submission"),
					h(
						"div",
						{ className: "flex items-center gap-4 text-sm" },
						h("span", { className: "text-gray-500" }, `${monthWorkDays} days`),
						h("span", { className: "text-gray-500" }, `${monthTotalHours.toFixed(1)}h`),
						monthOvertime !== 0 && h("span", { className: monthOvertime > 0 ? "text-amber-600" : "text-gray-500" }, `${monthOvertime > 0 ? "+" : ""}${monthOvertime.toFixed(1)}h OT`),
						isMonthSubmitted(selectedMonth.year, selectedMonth.month)
							? h("span", { className: "text-green-600 font-medium" }, "Submitted")
							: h("span", { className: "text-gray-400" }, "Pending"),
					),
				),
				h(
					"div",
					{ className: "flex items-center gap-2" },
					h(
						"select",
						{
							value: `${selectedMonth.year}-${selectedMonth.month}`,
							onChange: (e) => {
								const [y, m] = e.target.value.split("-").map(Number)
								setSelectedMonth({ year: y, month: m })
							},
							className: "border rounded px-2 py-1 text-sm",
						},
						getLastMonths().map((m) =>
							h("option", { key: `${m.year}-${m.month}`, value: `${m.year}-${m.month}` }, formatMonth(m.year, m.month)),
						),
					),
					h(
						"button",
						{
							onClick: openSubmissionModal,
							disabled: isMonthSubmitted(selectedMonth.year, selectedMonth.month) || monthRecords.length === 0,
							className: `px-3 py-1 rounded text-sm font-medium ${
								isMonthSubmitted(selectedMonth.year, selectedMonth.month) || monthRecords.length === 0
									? "bg-gray-100 text-gray-400 cursor-not-allowed"
									: "bg-blue-600 text-white hover:bg-blue-700"
							}`,
						},
						"Submit",
					),
					submissions.length > 0 &&
						h(
							"button",
							{
								onClick: () => {
									const el = document.getElementById("submission-history")
									if (el) el.open = !el.open
								},
								className: "text-gray-400 hover:text-gray-600 text-sm",
							},
							`(${submissions.length})`,
						),
				),
			),
			// Submission history (hidden by default)
			submissions.length > 0 &&
				h(
					"details",
					{ id: "submission-history", className: "mt-3" },
					h(
						"summary",
						{ className: "text-xs text-gray-500 cursor-pointer hover:text-gray-700" },
						"Submission History",
					),
					h(
						"div",
						{ className: "mt-2 space-y-1" },
						submissions.slice(0, 5).map((s) =>
							h(
								"div",
								{ key: s.id, className: "flex justify-between items-center bg-gray-50 p-2 rounded text-xs" },
								h(
									"div",
									null,
									h("span", { className: "font-medium" }, `${formatDate(s.period_start)} - ${formatDate(s.period_end)}`),
									h("span", { className: "text-gray-500 ml-2" }, `→ ${s.sent_to_email}`),
								),
								h(
									"span",
									{
										className: `px-2 py-0.5 rounded ${
											s.status === "sent"
												? "bg-green-100 text-green-800"
												: s.status === "failed"
													? "bg-red-100 text-red-800"
													: "bg-yellow-100 text-yellow-800"
										}`,
									},
									s.status.charAt(0).toUpperCase() + s.status.slice(1),
								),
							),
						),
					),
				),
		),

		// Add/Edit Entry Modal
		showAddModal &&
			h(
				React.Fragment,
				null,
				h(
					"div",
					{
						key: "modal-backdrop",
						className: "fixed inset-0 bg-black/50 z-40",
						onClick: closeModal,
					},
				),
				h(
					"div",
					{ key: "modal-container", className: "fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none" },
					h(
						"div",
						{
							className: "bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto",
							role: "dialog",
							"aria-modal": "true",
						},
						// Modal header with title and X close button
						h(
							"div",
							{ className: "flex items-center justify-between px-6 py-4 border-b border-gray-200" },
							h("h2", { className: "text-lg font-semibold text-gray-900" }, editingRecord ? "Edit Time Entry" : "Add Time Entry"),
							h(
								"button",
								{
									type: "button",
									onClick: closeModal,
									className: "text-gray-400 hover:text-gray-600 transition-colors",
								},
								h(
									"svg",
									{ className: "h-5 w-5", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", strokeWidth: 2 },
									h("path", { strokeLinecap: "round", strokeLinejoin: "round", d: "M6 18L18 6M6 6l12 12" }),
								),
							),
						),
						// Modal content
						h(
							"div",
							{ className: "flex-1 overflow-y-auto p-6" },
							h(
								"form",
								{ onSubmit: handleSaveEntry },
						// Date
						h(
							"div",
							{ className: "mb-4" },
							h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Date"),
							h("input", {
								type: "date",
								value: formData.date,
								onChange: (e) => setFormData({ ...formData, date: e.target.value }),
								className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
								required: true,
							}),
						),
						// Day Type
						h(
							"div",
							{ className: "mb-4" },
							h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Type"),
							h(
								"select",
								{
									value: formData.day_type,
									onChange: (e) => setFormData({ ...formData, day_type: e.target.value }),
									className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
									h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Check In"),
									h("input", {
										type: "time",
										value: formData.check_in,
										onChange: (e) => setFormData({ ...formData, check_in: e.target.value }),
										className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
									}),
								),
								// Check Out Time
								h(
									"div",
									{ className: "mb-4" },
									h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Check Out"),
									h("input", {
										type: "time",
										value: formData.check_out,
										onChange: (e) => setFormData({ ...formData, check_out: e.target.value }),
										className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
									}),
								),
								// Work Location
								h(
									"div",
									{ className: "mb-4" },
									h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Location"),
									h(
										"select",
										{
											value: formData.work_location,
											onChange: (e) => setFormData({ ...formData, work_location: e.target.value }),
											className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
							h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Notes"),
							h("textarea", {
								value: formData.notes,
								onChange: (e) => setFormData({ ...formData, notes: e.target.value }),
								className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
								rows: 2,
								placeholder: "Optional notes...",
							}),
						),
						// Buttons
						h(
							"div",
							{ className: "flex justify-end gap-3 pt-4" },
							h(
								"button",
								{
									type: "button",
									onClick: closeModal,
									className: "px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50",
								},
								"Cancel",
							),
							h(
								"button",
								{
									type: "submit",
									className: "px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700",
								},
								editingRecord ? "Update" : "Save",
							),
						),
					),
				),
			),
		),
	),

		// Submission Modal
		showSubmissionModal &&
			h(
				React.Fragment,
				null,
				h(
					"div",
					{
						key: "submission-backdrop",
						className: "fixed inset-0 bg-black/50 z-40",
						onClick: () => setShowSubmissionModal(false),
					},
				),
				h(
					"div",
					{ key: "submission-container", className: "fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none" },
					h(
						"div",
						{
							className: "bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto",
							role: "dialog",
							"aria-modal": "true",
						},
						// Modal header
						h(
							"div",
							{ className: "flex items-center justify-between px-6 py-4 border-b border-gray-200" },
							h("h2", { className: "text-lg font-semibold text-gray-900" }, "Submit Timesheet"),
							h(
								"button",
								{
									type: "button",
									onClick: () => setShowSubmissionModal(false),
									className: "text-gray-400 hover:text-gray-600 transition-colors",
								},
								h(
									"svg",
									{ className: "h-5 w-5", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", strokeWidth: 2 },
									h("path", { strokeLinecap: "round", strokeLinejoin: "round", d: "M6 18L18 6M6 6l12 12" }),
								),
							),
						),
						// Modal content
						h(
							"div",
							{ className: "flex-1 overflow-y-auto p-6" },
							// Period summary
							h(
								"div",
								{ className: "bg-gray-50 p-4 rounded mb-4" },
								h("p", { className: "text-sm text-gray-500" }, "Period"),
								h("p", { className: "font-semibold" }, formatMonth(selectedMonth.year, selectedMonth.month)),
								h(
									"div",
									{ className: "mt-2 text-sm text-gray-600" },
									`${monthWorkDays} work days · ${monthTotalHours.toFixed(1)} hours · ${monthRecords.length} records`,
								),
							),
							// Warning
							h(
								"div",
								{ className: "bg-amber-50 border border-amber-200 text-amber-800 p-3 rounded mb-4 text-sm" },
								"Once submitted, time records for this month will be locked and cannot be edited.",
							),
							// Recipient email
							h(
								"div",
								{ className: "mb-4" },
								h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Recipient Email"),
								h("input", {
									type: "email",
									value: recipientEmail,
									onChange: (e) => setRecipientEmail(e.target.value),
									className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
									placeholder: "hr@company.com",
									required: true,
								}),
							),
							// Notes
							h(
								"div",
								{ className: "mb-4" },
								h("label", { className: "block text-sm font-medium text-gray-700 mb-1" }, "Notes (optional)"),
								h("textarea", {
									value: submissionNotes,
									onChange: (e) => setSubmissionNotes(e.target.value),
									className: "w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
									rows: 2,
									placeholder: "Any additional notes...",
								}),
							),
							// Buttons
							h(
								"div",
								{ className: "flex justify-end gap-3 pt-4" },
								h(
									"button",
									{
										type: "button",
										onClick: () => setShowSubmissionModal(false),
										disabled: isSubmitting,
										className: "px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50",
									},
									"Cancel",
								),
								h(
									"button",
									{
										type: "button",
										onClick: handleSubmitMonth,
										disabled: isSubmitting || !recipientEmail,
										className: `px-4 py-2 rounded-md font-medium ${
											isSubmitting || !recipientEmail
												? "bg-gray-100 text-gray-400 cursor-not-allowed"
												: "bg-blue-600 text-white hover:bg-blue-700"
										}`,
									},
									isSubmitting ? "Submitting..." : "Submit",
								),
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
