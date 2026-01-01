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
};

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
	];
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
	];
}

/**
 * Widget for company detail page.
 */
export const widgets = {
	companyDetail: CompanyTimeSettingsWidget,
};

export async function onLoad() {
	console.log("[TimeTracking] Frontend module loaded");
}

export async function onUnload() {
	console.log("[TimeTracking] Frontend module unloaded");
}

// ============================================================================
// API Functions
// ============================================================================

async function apiGet(path) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		credentials: "include",
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `Request failed: ${response.status}`);
	}
	return response.json();
}

async function apiPost(path, data) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		credentials: "include",
		body: JSON.stringify(data),
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `Request failed: ${response.status}`);
	}
	return response.json();
}

async function apiPut(path, data) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "PUT",
		headers: { "Content-Type": "application/json" },
		credentials: "include",
		body: JSON.stringify(data),
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `Request failed: ${response.status}`);
	}
	return response.json();
}

async function apiDelete(path) {
	const response = await fetch(`/api/v1/plugin/time-tracking${path}`, {
		method: "DELETE",
		credentials: "include",
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || `Request failed: ${response.status}`);
	}
	return response.status === 204 ? null : response.json();
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
	const date = new Date(dateStr);
	return date.toLocaleDateString(undefined, {
		day: "2-digit",
		month: "2-digit",
		year: "numeric",
	});
}

/**
 * Format a time string for display.
 * @param {string|null} timeStr - Time string (HH:MM:SS or HH:MM)
 * @returns {string} Formatted time or "-"
 */
function formatTime(timeStr) {
	if (!timeStr) return "-";
	// Return just HH:MM portion
	return timeStr.substring(0, 5);
}

/**
 * Get the short day name for a date.
 * @param {string} dateStr - ISO date string
 * @returns {string} Short day name (Mon, Tue, etc.)
 */
function getDayName(dateStr) {
	const date = new Date(dateStr);
	return date.toLocaleDateString(undefined, { weekday: "short" });
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
};

const DAY_TYPE_COLORS = {
	work: "bg-green-100 text-green-800",
	vacation: "bg-blue-100 text-blue-800",
	sick: "bg-red-100 text-red-800",
	doctor_visit: "bg-orange-100 text-orange-800",
	public_holiday: "bg-purple-100 text-purple-800",
	comp_time: "bg-yellow-100 text-yellow-800",
	unpaid_leave: "bg-gray-100 text-gray-800",
	weekend: "bg-gray-50 text-gray-500",
};

// ============================================================================
// Main Time Tracking Page
// ============================================================================

const WORK_LOCATIONS = {
	office: "Office",
	remote: "Remote/Home",
	client_site: "Client Site",
	travel: "Travel",
};

function TimeTrackingPage() {
	const React = window.React;
	const { useState, useEffect } = React;
	const h = React.createElement;

	const [todayRecord, setTodayRecord] = useState(null);
	const [weekRecords, setWeekRecords] = useState([]);
	const [balance, setBalance] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [companies, setCompanies] = useState([]);
	const [selectedCompanyId, setSelectedCompanyId] = useState(null);
	const [showAddModal, setShowAddModal] = useState(false);
	const [editingRecord, setEditingRecord] = useState(null);
	// Phase 2: Submission state
	const [submissions, setSubmissions] = useState([]);
	const [selectedMonth, setSelectedMonth] = useState(() => {
		const now = new Date();
		return { year: now.getFullYear(), month: now.getMonth() + 1 };
	});
	const [showSubmissionModal, setShowSubmissionModal] = useState(false);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [recipientEmail, setRecipientEmail] = useState("");
	const [submissionNotes, setSubmissionNotes] = useState("");
	const [monthRecords, setMonthRecords] = useState([]);
	// Phase 3: Calendar view state
	const [viewMode, setViewMode] = useState("calendar"); // 'table' or 'calendar'
	const [calendarMonth, setCalendarMonth] = useState(() => {
		const now = new Date();
		return { year: now.getFullYear(), month: now.getMonth() + 1 };
	});
	const [selectedDay, setSelectedDay] = useState(null);
	const [calendarRecords, setCalendarRecords] = useState([]);
	// Multi-entry status tracking
	const [checkInStatus, setCheckInStatus] = useState(null);
	// Entry editing state
	const [editingEntry, setEditingEntry] = useState(null);
	const [entryFormData, setEntryFormData] = useState({
		check_in: "",
		check_out: "",
	});
	const [formData, setFormData] = useState({
		date: new Date().toISOString().split("T")[0],
		day_type: "work",
		check_in: "09:00",
		check_out: "17:00",
		work_location: "remote",
		notes: "",
	});

	// Helper to get company name from ID
	const getCompanyName = (id) =>
		companies.find((c) => c.id === id)?.name || "-";

	// Calculate week stats
	const weekWorkDays = weekRecords.filter((r) => r.day_type === "work").length;
	const weekTotalHours = weekRecords.reduce(
		(sum, r) => sum + (r.net_hours || 0),
		0,
	);
	const weekOvertime = Math.max(0, weekTotalHours - 40);

	// Calculate remaining work days in the current month
	const calculateRemainingWorkDays = () => {
		const today = new Date();
		const year = today.getFullYear();
		const month = today.getMonth();
		const lastDay = new Date(year, month + 1, 0).getDate();
		let remaining = 0;

		// Count weekdays from today to end of month
		for (let d = today.getDate(); d <= lastDay; d++) {
			const date = new Date(year, month, d);
			const dayOfWeek = date.getDay();
			// Skip weekends (0 = Sunday, 6 = Saturday)
			if (dayOfWeek !== 0 && dayOfWeek !== 6) {
				remaining++;
			}
		}

		// Subtract vacation and other non-work days from calendarRecords for remaining days
		const todayStr = today.toISOString().split("T")[0];
		const futureNonWorkDays = calendarRecords.filter((r) => {
			if (r.date < todayStr) return false;
			return r.day_type !== "work" && r.day_type !== "doctor_visit";
		}).length;

		return Math.max(0, remaining - futureNonWorkDays);
	};

	const remainingWorkDays = calculateRemainingWorkDays();

	// Generate last 12 months for dropdown
	const getLastMonths = () => {
		const months = [];
		const now = new Date();
		for (let i = 0; i < 12; i++) {
			const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
			months.push({ year: d.getFullYear(), month: d.getMonth() + 1 });
		}
		return months;
	};

	// Format month for display
	const formatMonth = (year, month) => {
		const d = new Date(year, month - 1, 1);
		return d.toLocaleDateString(undefined, { year: "numeric", month: "long" });
	};

	// Check if a month has been submitted
	const isMonthSubmitted = (year, month) => {
		return submissions.some((s) => {
			const start = new Date(s.period_start);
			return start.getFullYear() === year && start.getMonth() + 1 === month;
		});
	};

	// Calculate month stats from monthRecords
	const monthWorkDays = monthRecords.filter(
		(r) => r.day_type === "work",
	).length;
	const monthTotalHours = monthRecords.reduce(
		(sum, r) => sum + (r.net_hours || 0),
		0,
	);
	const monthOvertime = Math.max(0, monthTotalHours - monthWorkDays * 8);

	// Calendar helper functions
	const getCalendarDays = (year, month) => {
		const days = [];
		const firstDay = new Date(year, month - 1, 1);
		const lastDay = new Date(year, month, 0);

		// Adjust for Monday start (European week)
		let startOffset = firstDay.getDay() - 1;
		if (startOffset < 0) startOffset = 6;

		// Add previous month days
		const prevMonth = month === 1 ? 12 : month - 1;
		const prevYear = month === 1 ? year - 1 : year;
		const prevMonthLastDay = new Date(prevYear, prevMonth, 0).getDate();
		for (let i = startOffset - 1; i >= 0; i--) {
			days.push({
				day: prevMonthLastDay - i,
				month: prevMonth,
				year: prevYear,
				isCurrentMonth: false,
			});
		}

		// Add current month days
		for (let d = 1; d <= lastDay.getDate(); d++) {
			days.push({ day: d, month, year, isCurrentMonth: true });
		}

		// Add next month days to fill 6 rows (42 cells)
		const nextMonth = month === 12 ? 1 : month + 1;
		const nextYear = month === 12 ? year + 1 : year;
		let nextDay = 1;
		while (days.length < 42) {
			days.push({
				day: nextDay++,
				month: nextMonth,
				year: nextYear,
				isCurrentMonth: false,
			});
		}

		return days;
	};

	const getRecordForDate = (year, month, day) => {
		const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
		return calendarRecords.find((r) => r.date === dateStr);
	};

	const isToday = (year, month, day) => {
		const today = new Date();
		return (
			today.getFullYear() === year &&
			today.getMonth() + 1 === month &&
			today.getDate() === day
		);
	};

	const isWeekend = (year, month, day) => {
		const d = new Date(year, month - 1, day);
		return d.getDay() === 0 || d.getDay() === 6;
	};

	const navigateMonth = (direction) => {
		setCalendarMonth((prev) => {
			let newMonth = prev.month + direction;
			let newYear = prev.year;
			if (newMonth < 1) {
				newMonth = 12;
				newYear--;
			} else if (newMonth > 12) {
				newMonth = 1;
				newYear++;
			}
			return { year: newYear, month: newMonth };
		});
		setSelectedDay(null);
	};

	// Fetch companies on mount
	useEffect(() => {
		fetch("/api/v1/companies", { credentials: "include" })
			.then((r) => r.json())
			.then((data) => {
				setCompanies(data);
				if (data.length > 0) {
					setSelectedCompanyId(data[0].id);
				}
			})
			.catch(console.error);
	}, []);

	// Fetch data when company changes
	useEffect(() => {
		if (!selectedCompanyId) return;
		fetchData();
		fetchSubmissions();
		fetchStatus();
	}, [selectedCompanyId]);

	// Fetch month records when selectedMonth changes
	useEffect(() => {
		if (!selectedCompanyId) return;
		fetchMonthRecords();
	}, [selectedCompanyId, selectedMonth]);

	// Fetch calendar month records when calendarMonth changes
	useEffect(() => {
		if (!selectedCompanyId) return;
		fetchCalendarRecords();
	}, [selectedCompanyId, calendarMonth]);

	async function fetchData() {
		setLoading(true);
		setError(null);
		try {
			// Get today's record
			const today = await apiGet("/today").catch(() => null);
			setTodayRecord(today);

			// Get week records
			const now = new Date();
			const weekStart = new Date(now);
			weekStart.setDate(now.getDate() - now.getDay() + 1); // Monday
			const weekEnd = new Date(weekStart);
			weekEnd.setDate(weekStart.getDate() + 6);

			const fromDate = weekStart.toISOString().split("T")[0];
			const toDate = weekEnd.toISOString().split("T")[0];
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			);
			setWeekRecords(records);

			// Get leave balance
			const year = now.getFullYear();
			const bal = await apiGet(
				`/leave-balance?year=${year}&company_id=${selectedCompanyId}`,
			);
			setBalance(bal);
		} catch (e) {
			setError(e.message);
		} finally {
			setLoading(false);
		}
	}

	async function fetchSubmissions() {
		try {
			const data = await apiGet(`/submissions?company_id=${selectedCompanyId}`);
			setSubmissions(data.submissions || []);
		} catch (e) {
			console.error("Failed to fetch submissions:", e);
		}
	}

	async function fetchMonthRecords() {
		try {
			const { year, month } = selectedMonth;
			const lastDay = new Date(year, month, 0).getDate();
			const fromDate = `${year}-${String(month).padStart(2, "0")}-01`;
			const toDate = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			);
			setMonthRecords(records);
		} catch (e) {
			console.error("Failed to fetch month records:", e);
		}
	}

	async function fetchCalendarRecords() {
		try {
			const { year, month } = calendarMonth;
			const lastDay = new Date(year, month, 0).getDate();
			const fromDate = `${year}-${String(month).padStart(2, "0")}-01`;
			const toDate = `${year}-${String(month).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
			const records = await apiGet(
				`/records?from=${fromDate}&to=${toDate}&company_id=${selectedCompanyId}`,
			);
			setCalendarRecords(records);
		} catch (e) {
			console.error("Failed to fetch calendar records:", e);
		}
	}

	async function fetchStatus() {
		try {
			const data = await apiGet(`/status?company_id=${selectedCompanyId}`);
			setCheckInStatus(data);
		} catch (e) {
			console.error("Failed to fetch check-in status:", e);
			setCheckInStatus(null);
		}
	}

	async function handleCheckIn() {
		try {
			const data = {
				company_id: selectedCompanyId,
				work_location: "remote",
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			};
			await apiPost("/check-in", data);
			fetchData();
			fetchStatus();
			fetchCalendarRecords();
		} catch (e) {
			setError(e.message);
		}
	}

	async function handleCheckOut() {
		try {
			const data = {
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			};
			await apiPost("/check-out", data);
			fetchData();
			fetchStatus();
			fetchCalendarRecords();
		} catch (e) {
			setError(e.message);
		}
	}

	// Toggle handler for single button check-in/out
	async function handleToggleCheckInOut() {
		if (checkInStatus?.has_open_entry) {
			await handleCheckOut();
		} else {
			await handleCheckIn();
		}
	}

	// Calculate elapsed time since check-in
	function getElapsedTime() {
		if (!checkInStatus?.current_entry?.check_in) return null;
		const [h, m] = checkInStatus.current_entry.check_in.split(":").map(Number);
		const checkInDate = new Date();
		checkInDate.setHours(h, m, 0, 0);
		const now = new Date();
		const diffMs = now - checkInDate;
		if (diffMs < 0) return null;
		const diffMins = Math.floor(diffMs / 60000);
		const hours = Math.floor(diffMins / 60);
		const mins = diffMins % 60;
		return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
	}

	// Validate time entries - check_in must be at least 5 minutes before check_out
	function validateTimes(checkIn, checkOut) {
		if (!checkIn || !checkOut) return null;
		const [inH, inM] = checkIn.split(":").map(Number);
		const [outH, outM] = checkOut.split(":").map(Number);
		const inMinutes = inH * 60 + inM;
		const outMinutes = outH * 60 + outM;
		const diff = outMinutes - inMinutes;
		if (diff < 5) {
			return "Check out time must be at least 5 minutes after check in time";
		}
		return null;
	}

	async function handleSaveRecord(e) {
		e.preventDefault();
		setError(null);

		// Validate times for work days
		if (formData.day_type === "work") {
			const timeError = validateTimes(formData.check_in, formData.check_out);
			if (timeError) {
				setError(timeError);
				return;
			}
		}

		try {
			const data = {
				date: formData.date,
				day_type: formData.day_type,
				company_id: selectedCompanyId,
				work_location:
					formData.day_type === "work" ? formData.work_location : null,
				notes: formData.notes || null,
			};
			// Only add times for work days
			if (formData.day_type === "work" && formData.check_in) {
				data.check_in = `${formData.check_in}:00`;
			}
			if (formData.day_type === "work" && formData.check_out) {
				data.check_out = `${formData.check_out}:00`;
			}

			if (editingRecord) {
				await apiPut(`/records/${editingRecord.id}`, data);
			} else {
				await apiPost("/records", data);
			}

			closeModal();
			fetchData();
		} catch (e) {
			setError(e.message);
		}
	}

	function openEditModal(record) {
		setEditingRecord(record);
		setFormData({
			date: record.date,
			day_type: record.day_type,
			check_in: record.check_in ? record.check_in.substring(0, 5) : "09:00",
			check_out: record.check_out ? record.check_out.substring(0, 5) : "17:00",
			work_location: record.work_location || "remote",
			notes: record.notes || "",
		});
		setShowAddModal(true);
	}

	function closeModal() {
		setShowAddModal(false);
		setEditingRecord(null);
		setFormData({
			date: new Date().toISOString().split("T")[0],
			day_type: "work",
			check_in: "09:00",
			check_out: "17:00",
			work_location: "remote",
			notes: "",
		});
	}

	async function handleDeleteRecord(recordId) {
		if (!confirm("Are you sure you want to delete this time entry?")) {
			return;
		}
		try {
			await apiDelete(`/records/${recordId}`);
			fetchData();
		} catch (e) {
			setError(e.message);
		}
	}

	// Entry-level edit functions
	function openEntryEdit(entry) {
		setEditingEntry(entry);
		setEntryFormData({
			check_in: entry.check_in ? entry.check_in.substring(0, 5) : "",
			check_out: entry.check_out ? entry.check_out.substring(0, 5) : "",
		});
	}

	function closeEntryEdit() {
		setEditingEntry(null);
		setEntryFormData({ check_in: "", check_out: "" });
	}

	async function handleSaveEntry() {
		if (!editingEntry) return;
		try {
			await apiPut(`/entries/${editingEntry.id}`, {
				check_in: entryFormData.check_in || null,
				check_out: entryFormData.check_out || null,
			});
			closeEntryEdit();
			// Refresh data
			fetchData();
			fetchCalendarRecords();
			fetchStatus();
		} catch (e) {
			setError(e.message);
		}
	}

	async function handleDeleteEntry(entryId) {
		if (!confirm("Delete this time entry?")) return;
		try {
			await apiDelete(`/entries/${entryId}`);
			// Refresh data
			fetchData();
			fetchCalendarRecords();
			fetchStatus();
		} catch (e) {
			setError(e.message);
		}
	}

	async function handleSubmitMonth() {
		if (!recipientEmail) {
			setError("Please enter a recipient email address");
			return;
		}
		setIsSubmitting(true);
		setError(null);
		try {
			const { year, month } = selectedMonth;
			let url = `/submissions?year=${year}&month=${month}&company_id=${selectedCompanyId}&recipient_email=${encodeURIComponent(recipientEmail)}`;
			if (submissionNotes) {
				url += `&notes=${encodeURIComponent(submissionNotes)}`;
			}
			await apiPost(url, {});
			setShowSubmissionModal(false);
			setRecipientEmail("");
			setSubmissionNotes("");
			fetchSubmissions();
			fetchMonthRecords();
			fetchData(); // Refresh week records to show locked status
		} catch (e) {
			setError(e.message);
		} finally {
			setIsSubmitting(false);
		}
	}

	function openSubmissionModal() {
		setRecipientEmail("");
		setSubmissionNotes("");
		setShowSubmissionModal(true);
	}

	if (loading) {
		return h(
			"div",
			{ className: "p-6" },
			h("p", { className: "text-gray-500" }, "Loading..."),
		);
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
						className:
							"bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700",
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
			{
				className:
					"flex items-center justify-between bg-gray-50 rounded-lg p-4 mb-6",
			},
			h(
				"div",
				{ className: "flex items-center gap-6" },
				// Today status - based on checkInStatus
				h(
					"div",
					{ className: "flex items-center gap-3" },
					h("div", {
						className: `w-3 h-3 rounded-full ${checkInStatus?.has_open_entry ? "bg-green-500 animate-pulse" : "bg-gray-300"}`,
					}),
					h(
						"div",
						null,
						h("span", { className: "text-sm text-gray-500" }, "Today"),
						checkInStatus?.has_open_entry
							? h(
									"p",
									{ className: "font-medium text-green-700" },
									`Checked in: ${formatTime(checkInStatus.current_entry?.check_in)}`,
									getElapsedTime() &&
										h(
											"span",
											{ className: "text-gray-400 ml-1" },
											`(${getElapsedTime()})`,
										),
								)
							: checkInStatus?.has_record
								? h(
										"p",
										{ className: "font-medium" },
										`${checkInStatus.entry_count} ${checkInStatus.entry_count === 1 ? "entry" : "entries"}`,
										todayRecord?.net_hours &&
											h(
												"span",
												{ className: "text-gray-400 ml-1" },
												`(${todayRecord.net_hours.toFixed(1)}h)`,
											),
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
						h(
							"p",
							{ className: "font-semibold text-gray-900" },
							`${weekTotalHours.toFixed(1)}h`,
						),
					),
					h(
						"div",
						null,
						h("span", { className: "text-gray-500" }, "Overtime"),
						h(
							"p",
							{
								className: `font-semibold ${weekOvertime > 0 ? "text-amber-600" : "text-gray-400"}`,
							},
							weekOvertime > 0 ? `+${weekOvertime.toFixed(1)}h` : "0h",
						),
					),
					h(
						"div",
						null,
						h("span", { className: "text-gray-500" }, "Days Left"),
						h(
							"p",
							{ className: "font-semibold text-blue-600" },
							remainingWorkDays,
						),
					),
				),
			),
			// Single toggle button for check-in/out
			h(
				"button",
				{
					type: "button",
					onClick: handleToggleCheckInOut,
					className: checkInStatus?.has_open_entry
						? "px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
						: "px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors",
				},
				checkInStatus?.has_open_entry ? "Check Out" : "Check In",
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
							className:
								"px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded",
						},
						"<",
					),
					h(
						"span",
						{ className: "font-medium min-w-32 text-center" },
						formatMonth(calendarMonth.year, calendarMonth.month),
					),
					h(
						"button",
						{
							onClick: () => navigateMonth(1),
							className:
								"px-2 py-1 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded",
						},
						">",
					),
				),
		),

		// Main content area with sidebar layout (shared between calendar and table views)
		h(
			"div",
			{ className: "flex gap-6" },
			// Left column: Calendar or Table
			h(
				"div",
				{ className: "flex-1 min-w-0" },
				// Calendar grid (when calendar view is active)
				viewMode === "calendar" &&
					h(
						"div",
						{ className: "bg-white rounded-lg shadow" },
						// Day headers
						h(
							"div",
							{ className: "grid grid-cols-7 border-b" },
							["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) =>
								h(
									"div",
									{
										key: day,
										className:
											"px-2 py-2 text-center text-xs font-medium text-gray-500",
									},
									day,
								),
							),
						),
						// Calendar grid
						h(
							"div",
							{ className: "grid grid-cols-7" },
							getCalendarDays(calendarMonth.year, calendarMonth.month).map(
								(cell, idx) => {
									const record = cell.isCurrentMonth
										? getRecordForDate(cell.year, cell.month, cell.day)
										: null;
									const isTodayCell = isToday(cell.year, cell.month, cell.day);
									const isWeekendDay = isWeekend(
										cell.year,
										cell.month,
										cell.day,
									);
									const isSelected =
										selectedDay &&
										selectedDay.year === cell.year &&
										selectedDay.month === cell.month &&
										selectedDay.day === cell.day;

									return h(
										"div",
										{
											key: idx,
											onClick: () =>
												cell.isCurrentMonth && setSelectedDay(cell),
											className: `min-h-20 p-2 border-b border-r cursor-pointer transition-colors ${
												!cell.isCurrentMonth
													? "bg-gray-50 text-gray-400"
													: isWeekendDay
														? "bg-gray-50"
														: "bg-white hover:bg-blue-50"
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
													"div",
													{ className: "flex items-center gap-1" },
													h(
														"span",
														{
															className: `text-xs px-1.5 py-0.5 rounded ${DAY_TYPE_COLORS[record.day_type] || "bg-gray-100"}`,
														},
														DAY_TYPE_LABELS[record.day_type]?.substring(0, 4) ||
															record.day_type.substring(0, 4),
													),
													// Show entry count if multiple entries
													record.entries &&
														record.entries.length > 1 &&
														h(
															"span",
															{ className: "text-xs text-gray-400" },
															`×${record.entries.length}`,
														),
													// Pulse indicator for open entry
													record.has_open_entry &&
														h("span", {
															className:
																"w-2 h-2 bg-green-500 rounded-full animate-pulse",
														}),
												),
												record.net_hours &&
													h(
														"div",
														{ className: "text-xs text-gray-600 mt-0.5" },
														`${record.net_hours.toFixed(1)}h`,
													),
											),
									);
								},
							),
						),
					),
				// Week view table (when table view is active)
				// Flatten records to individual entries for table display
				viewMode === "table" &&
					(() => {
						// Create flattened array of entries with parent record info
						const tableRows = [];
						weekRecords.forEach((record) => {
							if (record.entries && record.entries.length > 0) {
								record.entries.forEach((entry, idx) => {
									tableRows.push({
										...entry,
										record,
										isFirstOfDay: idx === 0,
										entryIndex: idx + 1,
										totalEntries: record.entries.length,
									});
								});
							} else {
								// Fallback for records without entries array
								tableRows.push({
									id: `${record.id}-legacy`,
									record,
									isFirstOfDay: true,
									entryIndex: 1,
									totalEntries: 1,
									check_in: record.check_in,
									check_out: record.check_out,
									gross_minutes: record.gross_hours
										? Math.round(record.gross_hours * 60)
										: null,
								});
							}
						});
						return h(
							"div",
							{ className: "bg-white rounded-lg shadow overflow-hidden" },
							h(
								"table",
								{ className: "w-full" },
								h(
									"thead",
									{ className: "bg-gray-50" },
									h(
										"tr",
										null,
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Date",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Day",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Company",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Type",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"#",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Check In",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Check Out",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Duration",
										),
										h(
											"th",
											{
												className:
													"px-4 py-3 text-left text-sm font-medium text-gray-500",
											},
											"Actions",
										),
									),
								),
								h(
									"tbody",
									null,
									tableRows.length === 0
										? h(
												"tr",
												null,
												h(
													"td",
													{
														colSpan: 9,
														className: "px-4 py-8 text-center text-gray-500",
													},
													"No records this week",
												),
											)
										: tableRows.map((row, i) =>
												h(
													"tr",
													{
														key: row.id,
														className: `${row.isFirstOfDay ? "border-t border-gray-200" : ""} ${row.record.is_locked ? "opacity-60" : ""} cursor-pointer hover:bg-blue-50 ${!row.check_out ? "bg-green-50" : i % 2 === 0 ? "bg-white" : "bg-gray-50"}`,
														onClick: () => {
															const [year, month, day] = row.record.date
																.split("-")
																.map(Number);
															setSelectedDay({ year, month, day });
														},
													},
													// Date - only show for first entry of day
													h(
														"td",
														{ className: "px-4 py-2" },
														row.isFirstOfDay ? formatDate(row.record.date) : "",
													),
													// Day name - only show for first entry of day
													h(
														"td",
														{ className: "px-4 py-2" },
														row.isFirstOfDay ? getDayName(row.record.date) : "",
													),
													// Company - only show for first entry of day
													h(
														"td",
														{ className: "px-4 py-2 text-gray-600" },
														row.isFirstOfDay
															? getCompanyName(row.record.company_id)
															: "",
													),
													// Type - only show for first entry of day
													h(
														"td",
														{ className: "px-4 py-2" },
														row.isFirstOfDay
															? h(
																	"span",
																	{
																		className: `px-2 py-1 rounded text-xs ${DAY_TYPE_COLORS[row.record.day_type] || "bg-gray-100"}`,
																	},
																	DAY_TYPE_LABELS[row.record.day_type] ||
																		row.record.day_type,
																)
															: "",
													),
													// Entry number
													h(
														"td",
														{
															className: "px-4 py-2 text-xs text-gray-400",
														},
														`${row.entryIndex}/${row.totalEntries}`,
													),
													// Check In
													h(
														"td",
														{ className: "px-4 py-2" },
														formatTime(row.check_in),
													),
													// Check Out
													h(
														"td",
														{ className: "px-4 py-2" },
														row.check_out
															? formatTime(row.check_out)
															: h(
																	"span",
																	{
																		className: "text-green-600 font-medium",
																	},
																	"ongoing",
																),
													),
													// Duration
													h(
														"td",
														{ className: "px-4 py-2" },
														row.gross_minutes
															? `${Math.floor(row.gross_minutes / 60)}h ${row.gross_minutes % 60}m`
															: "-",
													),
													// Actions
													h(
														"td",
														{ className: "px-4 py-2" },
														row.record.is_locked
															? row.isFirstOfDay
																? h(
																		"span",
																		{
																			className:
																				"px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs",
																		},
																		"Locked",
																	)
																: null
															: h(
																	"div",
																	{ className: "flex gap-2" },
																	h(
																		"button",
																		{
																			onClick: (e) => {
																				e.stopPropagation();
																				openEntryEdit(row);
																			},
																			className:
																				"text-gray-400 hover:text-blue-600 text-sm",
																		},
																		"Edit",
																	),
																	h(
																		"button",
																		{
																			onClick: (e) => {
																				e.stopPropagation();
																				handleDeleteEntry(row.id);
																			},
																			className:
																				"text-gray-400 hover:text-red-600 text-sm",
																		},
																		"Delete",
																	),
																),
													),
												),
											),
								),
							),
						);
					})(),
			),
			// Right column: Sidebar with Leave Balance + Monthly Submission (always visible)
			h(
				"div",
				{ className: "w-72 flex-shrink-0 space-y-4" },
				// Leave Balance card
				balance &&
					h(
						"div",
						{ className: "bg-white rounded-lg shadow p-4" },
						h(
							"h3",
							{ className: "text-sm font-semibold text-gray-700 mb-3" },
							"Leave Balance",
						),
						h(
							"div",
							{ className: "space-y-3" },
							h(
								"div",
								{ className: "flex justify-between items-center" },
								h(
									"span",
									{ className: "text-sm text-gray-600" },
									"Vacation Days",
								),
								h(
									"span",
									{ className: "text-lg font-bold text-green-600" },
									balance.vacation_remaining,
								),
							),
							h(
								"div",
								{ className: "flex justify-between items-center" },
								h("span", { className: "text-sm text-gray-600" }, "Comp Time"),
								h(
									"span",
									{ className: "text-lg font-bold text-blue-600" },
									`${balance.comp_time_balance?.toFixed(1) || 0}h`,
								),
							),
							h(
								"div",
								{ className: "flex justify-between items-center" },
								h(
									"span",
									{ className: "text-sm text-gray-600" },
									"Sick Days Used",
								),
								h(
									"span",
									{ className: "text-lg font-bold text-gray-600" },
									balance.sick_days_taken,
								),
							),
						),
					),
				// Monthly Submission card
				h(
					"div",
					{ className: "bg-white rounded-lg shadow p-4" },
					h(
						"h3",
						{ className: "text-sm font-semibold text-gray-700 mb-3" },
						"Monthly Submission",
					),
					h(
						"div",
						{ className: "space-y-3" },
						// Month selector
						h(
							"select",
							{
								value: `${selectedMonth.year}-${selectedMonth.month}`,
								onChange: (e) => {
									const [y, m] = e.target.value.split("-").map(Number);
									setSelectedMonth({ year: y, month: m });
								},
								className:
									"w-full border border-gray-300 rounded-md px-3 py-2 text-sm",
							},
							getLastMonths().map((m) =>
								h(
									"option",
									{
										key: `${m.year}-${m.month}`,
										value: `${m.year}-${m.month}`,
									},
									formatMonth(m.year, m.month),
								),
							),
						),
						// Stats
						h(
							"div",
							{ className: "grid grid-cols-2 gap-2 text-sm" },
							h("div", { className: "text-gray-500" }, "Work Days:"),
							h("div", { className: "text-right font-medium" }, monthWorkDays),
							h("div", { className: "text-gray-500" }, "Total Hours:"),
							h(
								"div",
								{ className: "text-right font-medium" },
								`${monthTotalHours.toFixed(1)}h`,
							),
							monthOvertime !== 0 &&
								h("div", { className: "text-gray-500" }, "Overtime:"),
							monthOvertime !== 0 &&
								h(
									"div",
									{
										className: `text-right font-medium ${monthOvertime > 0 ? "text-amber-600" : "text-gray-600"}`,
									},
									`${monthOvertime > 0 ? "+" : ""}${monthOvertime.toFixed(1)}h`,
								),
						),
						// Status + Submit button
						h(
							"div",
							{ className: "flex items-center justify-between pt-2 border-t" },
							isMonthSubmitted(selectedMonth.year, selectedMonth.month)
								? h(
										"span",
										{ className: "text-sm text-green-600 font-medium" },
										"Submitted",
									)
								: h("span", { className: "text-sm text-gray-400" }, "Pending"),
							h(
								"button",
								{
									onClick: openSubmissionModal,
									disabled:
										isMonthSubmitted(selectedMonth.year, selectedMonth.month) ||
										monthRecords.length === 0,
									className: `px-3 py-1.5 rounded text-sm font-medium ${
										isMonthSubmitted(selectedMonth.year, selectedMonth.month) ||
										monthRecords.length === 0
											? "bg-gray-100 text-gray-400 cursor-not-allowed"
											: "bg-blue-600 text-white hover:bg-blue-700"
									}`,
								},
								"Submit",
							),
						),
						// Submission history link
						submissions.length > 0 &&
							h(
								"details",
								{ className: "text-xs" },
								h(
									"summary",
									{
										className:
											"text-gray-500 cursor-pointer hover:text-gray-700",
									},
									`${submissions.length} previous submission${submissions.length > 1 ? "s" : ""}`,
								),
								h(
									"div",
									{ className: "mt-2 space-y-1" },
									submissions.slice(0, 3).map((s) =>
										h(
											"div",
											{
												key: s.id,
												className: "flex justify-between items-center text-xs",
											},
											h(
												"span",
												{ className: "text-gray-600" },
												formatMonth(
													new Date(s.period_start).getFullYear(),
													new Date(s.period_start).getMonth() + 1,
												),
											),
											h(
												"span",
												{
													className: `px-1.5 py-0.5 rounded ${
														s.status === "sent"
															? "bg-green-100 text-green-700"
															: s.status === "failed"
																? "bg-red-100 text-red-700"
																: "bg-yellow-100 text-yellow-700"
													}`,
												},
												s.status,
											),
										),
									),
								),
							),
					),
				),
			),
		),

		// Day Detail Modal (when a day is selected)
		selectedDay &&
			h(
				React.Fragment,
				null,
				h("div", {
					key: "detail-backdrop",
					className: "fixed inset-0 bg-black/50 z-40",
					onClick: () => setSelectedDay(null),
				}),
				h(
					"div",
					{
						key: "detail-container",
						className:
							"fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none",
					},
					h(
						"div",
						{
							className:
								"bg-white rounded-lg shadow-xl w-full max-w-md pointer-events-auto",
							role: "dialog",
							"aria-modal": "true",
						},
						// Modal header
						h(
							"div",
							{
								className:
									"flex items-center justify-between px-6 py-4 border-b border-gray-200",
							},
							h(
								"div",
								null,
								h(
									"h2",
									{ className: "text-lg font-semibold text-gray-900" },
									formatDate(
										`${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`,
									),
								),
								h(
									"p",
									{ className: "text-sm text-gray-500" },
									getDayName(
										`${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`,
									),
								),
							),
							h(
								"button",
								{
									type: "button",
									onClick: () => setSelectedDay(null),
									className:
										"text-gray-400 hover:text-gray-600 transition-colors",
								},
								h(
									"svg",
									{
										className: "h-5 w-5",
										fill: "none",
										viewBox: "0 0 24 24",
										stroke: "currentColor",
										strokeWidth: 2,
									},
									h("path", {
										strokeLinecap: "round",
										strokeLinejoin: "round",
										d: "M6 18L18 6M6 6l12 12",
									}),
								),
							),
						),
						// Modal content
						h(
							"div",
							{ className: "p-6" },
							(() => {
								const dayRecord = getRecordForDate(
									selectedDay.year,
									selectedDay.month,
									selectedDay.day,
								);
								if (!dayRecord) {
									return h(
										"div",
										{ className: "text-center py-6" },
										h(
											"p",
											{ className: "text-gray-500 mb-4" },
											"No record for this day.",
										),
										h(
											"button",
											{
												onClick: () => {
													setFormData({
														...formData,
														date: `${selectedDay.year}-${String(selectedDay.month).padStart(2, "0")}-${String(selectedDay.day).padStart(2, "0")}`,
													});
													setSelectedDay(null);
													setShowAddModal(true);
												},
												className:
													"px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700",
											},
											"Add Entry",
										),
									);
								}
								return h(
									"div",
									null,
									// Company name
									h(
										"div",
										{ className: "mb-4" },
										h(
											"span",
											{ className: "text-sm text-gray-500" },
											"Company",
										),
										h(
											"p",
											{ className: "font-medium text-gray-900" },
											getCompanyName(dayRecord.company_id),
										),
									),
									// Type badge and lock status
									h(
										"div",
										{ className: "flex items-center gap-2 mb-4" },
										h(
											"span",
											{
												className: `px-2 py-1 rounded text-sm ${DAY_TYPE_COLORS[dayRecord.day_type] || "bg-gray-100"}`,
											},
											DAY_TYPE_LABELS[dayRecord.day_type] || dayRecord.day_type,
										),
										dayRecord.is_locked &&
											h(
												"span",
												{
													className:
														"px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs",
												},
												"Locked",
											),
									),
									// Time entries (multi-entry support)
									dayRecord.day_type === "work" &&
										h(
											"div",
											{ className: "mb-4" },
											// Entries timeline
											dayRecord.entries && dayRecord.entries.length > 0
												? h(
														"div",
														{ className: "space-y-2 mb-4" },
														h(
															"span",
															{ className: "text-sm text-gray-500 block mb-2" },
															`Time Entries (${dayRecord.entries.length})`,
														),
														dayRecord.entries.map((entry, idx) =>
															editingEntry?.id === entry.id
																? // Inline edit form
																	h(
																		"div",
																		{
																			key: entry.id,
																			className:
																				"p-3 bg-blue-50 border border-blue-200 rounded",
																		},
																		h(
																			"div",
																			{
																				className:
																					"flex items-center gap-2 mb-2",
																			},
																			h(
																				"span",
																				{
																					className: "text-xs text-gray-500",
																				},
																				`#${idx + 1}`,
																			),
																			h("input", {
																				type: "time",
																				value: entryFormData.check_in,
																				onChange: (e) =>
																					setEntryFormData((p) => ({
																						...p,
																						check_in: e.target.value,
																					})),
																				className:
																					"border rounded px-2 py-1 text-sm",
																			}),
																			h(
																				"span",
																				{ className: "text-gray-400" },
																				"-",
																			),
																			h("input", {
																				type: "time",
																				value: entryFormData.check_out,
																				onChange: (e) =>
																					setEntryFormData((p) => ({
																						...p,
																						check_out: e.target.value,
																					})),
																				className:
																					"border rounded px-2 py-1 text-sm",
																			}),
																		),
																		h(
																			"div",
																			{ className: "flex gap-2" },
																			h(
																				"button",
																				{
																					type: "button",
																					onClick: handleSaveEntry,
																					className:
																						"px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700",
																				},
																				"Save",
																			),
																			h(
																				"button",
																				{
																					type: "button",
																					onClick: closeEntryEdit,
																					className:
																						"px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300",
																				},
																				"Cancel",
																			),
																		),
																	)
																: // Normal display with edit/delete buttons
																	h(
																		"div",
																		{
																			key: entry.id,
																			className: `flex items-center justify-between p-2 rounded ${entry.check_out ? "bg-gray-50" : "bg-green-50 border border-green-200"}`,
																		},
																		h(
																			"div",
																			{
																				className: "flex items-center gap-2",
																			},
																			h(
																				"span",
																				{
																					className:
																						"text-xs text-gray-400 w-4",
																				},
																				`#${idx + 1}`,
																			),
																			h(
																				"span",
																				{ className: "font-medium" },
																				formatTime(entry.check_in),
																			),
																			h(
																				"span",
																				{ className: "text-gray-400" },
																				"-",
																			),
																			entry.check_out
																				? h(
																						"span",
																						{ className: "font-medium" },
																						formatTime(entry.check_out),
																					)
																				: h(
																						"span",
																						{
																							className:
																								"text-green-600 font-medium",
																						},
																						"ongoing",
																					),
																			entry.gross_minutes
																				? h(
																						"span",
																						{
																							className:
																								"text-sm text-gray-500 ml-2",
																						},
																						`(${Math.floor(entry.gross_minutes / 60)}h ${entry.gross_minutes % 60}m)`,
																					)
																				: null,
																		),
																		// Edit/Delete buttons
																		!dayRecord.is_locked &&
																			h(
																				"div",
																				{
																					className: "flex items-center gap-1",
																				},
																				h(
																					"button",
																					{
																						type: "button",
																						onClick: () => openEntryEdit(entry),
																						className:
																							"p-1 text-gray-400 hover:text-blue-600",
																						title: "Edit entry",
																					},
																					h(
																						"svg",
																						{
																							className: "w-4 h-4",
																							fill: "none",
																							stroke: "currentColor",
																							viewBox: "0 0 24 24",
																						},
																						h("path", {
																							strokeLinecap: "round",
																							strokeLinejoin: "round",
																							strokeWidth: 2,
																							d: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
																						}),
																					),
																				),
																				h(
																					"button",
																					{
																						type: "button",
																						onClick: () =>
																							handleDeleteEntry(entry.id),
																						className:
																							"p-1 text-gray-400 hover:text-red-600",
																						title: "Delete entry",
																					},
																					h(
																						"svg",
																						{
																							className: "w-4 h-4",
																							fill: "none",
																							stroke: "currentColor",
																							viewBox: "0 0 24 24",
																						},
																						h("path", {
																							strokeLinecap: "round",
																							strokeLinejoin: "round",
																							strokeWidth: 2,
																							d: "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
																						}),
																					),
																				),
																			),
																	),
														),
													)
												: h(
														"div",
														{ className: "grid grid-cols-2 gap-4" },
														h(
															"div",
															null,
															h(
																"span",
																{ className: "text-sm text-gray-500 block" },
																"Check In",
															),
															h(
																"span",
																{ className: "font-medium" },
																formatTime(dayRecord.check_in),
															),
														),
														h(
															"div",
															null,
															h(
																"span",
																{ className: "text-sm text-gray-500 block" },
																"Check Out",
															),
															h(
																"span",
																{ className: "font-medium" },
																formatTime(dayRecord.check_out),
															),
														),
													),
											// Summary row
											h(
												"div",
												{
													className:
														"flex justify-between items-center pt-3 border-t mt-3",
												},
												h(
													"div",
													{ className: "text-sm" },
													h("span", { className: "text-gray-500" }, "Break: "),
													h(
														"span",
														{ className: "font-medium" },
														dayRecord.break_minutes
															? `${dayRecord.break_minutes} min`
															: "-",
													),
												),
												h(
													"div",
													{ className: "text-sm" },
													h("span", { className: "text-gray-500" }, "Net: "),
													h(
														"span",
														{ className: "font-semibold text-gray-900" },
														dayRecord.net_hours
															? `${dayRecord.net_hours.toFixed(1)}h`
															: "-",
													),
												),
											),
										),
									// Work location
									dayRecord.work_location &&
										h(
											"div",
											{ className: "mb-4" },
											h(
												"span",
												{ className: "text-sm text-gray-500 block" },
												"Location",
											),
											h(
												"span",
												{ className: "font-medium" },
												WORK_LOCATIONS[dayRecord.work_location] ||
													dayRecord.work_location,
											),
										),
									// Notes
									dayRecord.notes &&
										h(
											"div",
											{ className: "mb-4" },
											h(
												"span",
												{ className: "text-sm text-gray-500 block" },
												"Notes",
											),
											h("p", { className: "text-gray-700" }, dayRecord.notes),
										),
									// Action buttons
									!dayRecord.is_locked &&
										h(
											"div",
											{ className: "flex gap-3 pt-4 border-t" },
											h(
												"button",
												{
													onClick: () => {
														setSelectedDay(null);
														openEditModal(dayRecord);
													},
													className:
														"flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors",
												},
												h(
													"svg",
													{
														className: "w-4 h-4",
														fill: "none",
														viewBox: "0 0 24 24",
														stroke: "currentColor",
														strokeWidth: 2,
													},
													h("path", {
														strokeLinecap: "round",
														strokeLinejoin: "round",
														d: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
													}),
												),
												"Edit",
											),
											h(
												"button",
												{
													onClick: () => {
														setSelectedDay(null);
														handleDeleteRecord(dayRecord.id);
													},
													className:
														"flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-600 bg-red-50 hover:bg-red-100 rounded-md transition-colors",
												},
												h(
													"svg",
													{
														className: "w-4 h-4",
														fill: "none",
														viewBox: "0 0 24 24",
														stroke: "currentColor",
														strokeWidth: 2,
													},
													h("path", {
														strokeLinecap: "round",
														strokeLinejoin: "round",
														d: "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
													}),
												),
												"Delete",
											),
										),
								);
							})(),
						),
					),
				),
			),

		// Add/Edit Entry Modal
		showAddModal &&
			h(
				React.Fragment,
				null,
				h("div", {
					key: "modal-backdrop",
					className: "fixed inset-0 bg-black/50 z-40",
					onClick: closeModal,
				}),
				h(
					"div",
					{
						key: "modal-container",
						className:
							"fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none",
					},
					h(
						"div",
						{
							className:
								"bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto",
							role: "dialog",
							"aria-modal": "true",
						},
						// Modal header with title and X close button
						h(
							"div",
							{
								className:
									"flex items-center justify-between px-6 py-4 border-b border-gray-200",
							},
							h(
								"h2",
								{ className: "text-lg font-semibold text-gray-900" },
								editingRecord ? "Edit Time Entry" : "Add Time Entry",
							),
							h(
								"button",
								{
									type: "button",
									onClick: closeModal,
									className:
										"text-gray-400 hover:text-gray-600 transition-colors",
								},
								h(
									"svg",
									{
										className: "h-5 w-5",
										fill: "none",
										viewBox: "0 0 24 24",
										stroke: "currentColor",
										strokeWidth: 2,
									},
									h("path", {
										strokeLinecap: "round",
										strokeLinejoin: "round",
										d: "M6 18L18 6M6 6l12 12",
									}),
								),
							),
						),
						// Modal content
						h(
							"div",
							{ className: "flex-1 overflow-y-auto p-6" },
							h(
								"form",
								{ onSubmit: handleSaveRecord },
								// Date
								h(
									"div",
									{ className: "mb-4" },
									h(
										"label",
										{
											className: "block text-sm font-medium text-gray-700 mb-1",
										},
										"Date",
									),
									h("input", {
										type: "date",
										value: formData.date,
										onChange: (e) =>
											setFormData({ ...formData, date: e.target.value }),
										className:
											"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
										required: true,
									}),
								),
								// Day Type
								h(
									"div",
									{ className: "mb-4" },
									h(
										"label",
										{
											className: "block text-sm font-medium text-gray-700 mb-1",
										},
										"Type",
									),
									h(
										"select",
										{
											value: formData.day_type,
											onChange: (e) =>
												setFormData({ ...formData, day_type: e.target.value }),
											className:
												"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
											h(
												"label",
												{
													className:
														"block text-sm font-medium text-gray-700 mb-1",
												},
												"Check In",
											),
											h("input", {
												type: "time",
												value: formData.check_in,
												onChange: (e) =>
													setFormData({
														...formData,
														check_in: e.target.value,
													}),
												className:
													"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
											}),
										),
										// Check Out Time
										h(
											"div",
											{ className: "mb-4" },
											h(
												"label",
												{
													className:
														"block text-sm font-medium text-gray-700 mb-1",
												},
												"Check Out",
											),
											h("input", {
												type: "time",
												value: formData.check_out,
												onChange: (e) =>
													setFormData({
														...formData,
														check_out: e.target.value,
													}),
												className:
													"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
											}),
										),
										// Work Location
										h(
											"div",
											{ className: "mb-4" },
											h(
												"label",
												{
													className:
														"block text-sm font-medium text-gray-700 mb-1",
												},
												"Location",
											),
											h(
												"select",
												{
													value: formData.work_location,
													onChange: (e) =>
														setFormData({
															...formData,
															work_location: e.target.value,
														}),
													className:
														"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
									h(
										"label",
										{
											className: "block text-sm font-medium text-gray-700 mb-1",
										},
										"Notes",
									),
									h("textarea", {
										value: formData.notes,
										onChange: (e) =>
											setFormData({ ...formData, notes: e.target.value }),
										className:
											"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
											className:
												"px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50",
										},
										"Cancel",
									),
									h(
										"button",
										{
											type: "submit",
											className:
												"px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700",
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
				h("div", {
					key: "submission-backdrop",
					className: "fixed inset-0 bg-black/50 z-40",
					onClick: () => setShowSubmissionModal(false),
				}),
				h(
					"div",
					{
						key: "submission-container",
						className:
							"fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none",
					},
					h(
						"div",
						{
							className:
								"bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto",
							role: "dialog",
							"aria-modal": "true",
						},
						// Modal header
						h(
							"div",
							{
								className:
									"flex items-center justify-between px-6 py-4 border-b border-gray-200",
							},
							h(
								"h2",
								{ className: "text-lg font-semibold text-gray-900" },
								"Submit Timesheet",
							),
							h(
								"button",
								{
									type: "button",
									onClick: () => setShowSubmissionModal(false),
									className:
										"text-gray-400 hover:text-gray-600 transition-colors",
								},
								h(
									"svg",
									{
										className: "h-5 w-5",
										fill: "none",
										viewBox: "0 0 24 24",
										stroke: "currentColor",
										strokeWidth: 2,
									},
									h("path", {
										strokeLinecap: "round",
										strokeLinejoin: "round",
										d: "M6 18L18 6M6 6l12 12",
									}),
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
								h(
									"p",
									{ className: "font-semibold" },
									formatMonth(selectedMonth.year, selectedMonth.month),
								),
								h(
									"div",
									{ className: "mt-2 text-sm text-gray-600" },
									`${monthWorkDays} work days · ${monthTotalHours.toFixed(1)} hours · ${monthRecords.length} records`,
								),
							),
							// Warning
							h(
								"div",
								{
									className:
										"bg-amber-50 border border-amber-200 text-amber-800 p-3 rounded mb-4 text-sm",
								},
								"Once submitted, time records for this month will be locked and cannot be edited.",
							),
							// Recipient email
							h(
								"div",
								{ className: "mb-4" },
								h(
									"label",
									{ className: "block text-sm font-medium text-gray-700 mb-1" },
									"Recipient Email",
								),
								h("input", {
									type: "email",
									value: recipientEmail,
									onChange: (e) => setRecipientEmail(e.target.value),
									className:
										"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
									placeholder: "hr@company.com",
									required: true,
								}),
							),
							// Notes
							h(
								"div",
								{ className: "mb-4" },
								h(
									"label",
									{ className: "block text-sm font-medium text-gray-700 mb-1" },
									"Notes (optional)",
								),
								h("textarea", {
									value: submissionNotes,
									onChange: (e) => setSubmissionNotes(e.target.value),
									className:
										"w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
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
										className:
											"px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50",
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
	);
}

// ============================================================================
// Company Time Settings Widget (for company detail page injection)
// ============================================================================

function CompanyTimeSettingsWidget({ companyId }) {
	const React = window.React;
	const { useState, useEffect } = React;
	const h = React.createElement;

	const [settings, setSettings] = useState(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		if (!companyId) return;
		apiGet(`/settings/company/${companyId}`)
			.then(setSettings)
			.catch(console.error)
			.finally(() => setLoading(false));
	}, [companyId]);

	if (loading) {
		return h(
			"div",
			{ className: "p-4 text-gray-500" },
			"Loading time settings...",
		);
	}

	if (!settings) {
		return null;
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
				h(
					"span",
					{ className: "font-medium" },
					settings.vacation_days_per_year,
				),
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
	);
}

// Default export for the plugin loader
export default {
	manifest,
	getNavItems,
	getRoutes,
	widgets,
	onLoad,
	onUnload,
};
