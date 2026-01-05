// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Time Tracking Plugin API Client
 *
 * API functions for communicating with the time-tracking backend endpoints.
 * Updated for simplified TimeEntry-only architecture.
 */

import type {
	CheckInRequest,
	CheckInStatusResponse,
	CheckOutRequest,
	CompanyTimeSettings,
	CompanyTimeSettingsUpdate,
	DailySummary,
	EntryType,
	Holiday,
	LeaveBalanceResponse,
	MonthlyReportResponse,
	TimeEntry,
	TimeEntryCreate,
	TimeEntryUpdate,
	Uuid,
	WorkLocation,
} from "./types";

const PLUGIN_API_BASE = "/api/v1/plugin/time-tracking";

class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
	) {
		super(message);
		this.name = "ApiError";
	}
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const response = await fetch(`${PLUGIN_API_BASE}${path}`, {
		...options,
		headers: {
			"Content-Type": "application/json",
			...options?.headers,
		},
		credentials: "include",
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new ApiError(response.status, error.detail || "Request failed");
	}

	// Handle 204 No Content (e.g., from DELETE requests)
	if (response.status === 204) {
		return undefined as T;
	}

	return response.json();
}

// Time Entries API
export const timeEntriesApi = {
	/**
	 * List time entries with optional filters.
	 */
	list: (params?: {
		company_id?: Uuid;
		start_date?: string;
		end_date?: string;
		entry_type?: EntryType;
	}): Promise<TimeEntry[]> => {
		const searchParams = new URLSearchParams();
		if (params?.company_id) searchParams.set("company_id", params.company_id);
		if (params?.start_date) searchParams.set("from", params.start_date);
		if (params?.end_date) searchParams.set("to", params.end_date);
		if (params?.entry_type) searchParams.set("entry_type", params.entry_type);

		const query = searchParams.toString();
		return request<TimeEntry[]>(`/entries${query ? `?${query}` : ""}`);
	},

	/**
	 * Get a single time entry by ID.
	 */
	get: (entryId: Uuid): Promise<TimeEntry> => {
		return request<TimeEntry>(`/entries/${entryId}`);
	},

	/**
	 * Create a new time entry.
	 */
	create: (data: TimeEntryCreate): Promise<TimeEntry> => {
		return request<TimeEntry>("/entries", {
			method: "POST",
			body: JSON.stringify(data),
		});
	},

	/**
	 * Update an existing time entry.
	 */
	update: (entryId: Uuid, data: TimeEntryUpdate): Promise<TimeEntry> => {
		return request<TimeEntry>(`/entries/${entryId}`, {
			method: "PUT",
			body: JSON.stringify(data),
		});
	},

	/**
	 * Delete a time entry.
	 */
	delete: (entryId: Uuid): Promise<void> => {
		return request<void>(`/entries/${entryId}`, {
			method: "DELETE",
		});
	},

	/**
	 * Get all entries for today.
	 */
	getToday: (): Promise<TimeEntry[]> => {
		return request<TimeEntry[]>("/today");
	},

	/**
	 * Get daily summary with aggregated data.
	 */
	getDailySummary: (date: string, companyId?: Uuid): Promise<DailySummary> => {
		const params = new URLSearchParams();
		params.set("date", date);
		if (companyId) params.set("company_id", companyId);
		return request<DailySummary>(`/daily-summary?${params.toString()}`);
	},

	/**
	 * Get current check-in status.
	 */
	getStatus: (): Promise<CheckInStatusResponse> => {
		return request<CheckInStatusResponse>("/status");
	},

	/**
	 * Check in - creates a new work entry with check_in time.
	 */
	checkIn: (data?: CheckInRequest): Promise<TimeEntry> => {
		const payload: CheckInRequest = {
			...data,
			timezone:
				data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
		};
		return request<TimeEntry>("/check-in", {
			method: "POST",
			body: JSON.stringify(payload),
		});
	},

	/**
	 * Check out - closes the open entry with check_out time.
	 */
	checkOut: (data?: CheckOutRequest): Promise<TimeEntry> => {
		const payload: CheckOutRequest = {
			...data,
			timezone:
				data?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
		};
		return request<TimeEntry>("/check-out", {
			method: "POST",
			body: JSON.stringify(payload),
		});
	},
};

// Legacy alias for backward compatibility
export const timeRecordsApi = {
	list: timeEntriesApi.list,
	get: timeEntriesApi.get,
	create: timeEntriesApi.create,
	update: timeEntriesApi.update,
	delete: timeEntriesApi.delete,
	getToday: () => timeEntriesApi.getToday(),
	checkIn: (companyId: Uuid, workLocation?: WorkLocation) =>
		timeEntriesApi.checkIn({ company_id: companyId, work_location: workLocation }),
	checkOut: () => timeEntriesApi.checkOut(),
};

// Leave Balance API
export const leaveBalanceApi = {
	/**
	 * Get leave balance for the current user.
	 */
	get: (year?: number, companyId?: Uuid): Promise<LeaveBalanceResponse> => {
		const params = new URLSearchParams();
		if (year) params.set("year", String(year));
		if (companyId) params.set("company_id", companyId);
		const query = params.toString();
		return request<LeaveBalanceResponse>(
			`/leave-balance${query ? `?${query}` : ""}`,
		);
	},
};

// Company Settings API
export const companySettingsApi = {
	/**
	 * Get time settings for a company.
	 */
	get: (companyId: Uuid): Promise<CompanyTimeSettings | null> => {
		return request<CompanyTimeSettings | null>(
			`/settings/company/${companyId}`,
		);
	},

	/**
	 * Update time settings for a company.
	 */
	update: (
		companyId: Uuid,
		data: CompanyTimeSettingsUpdate,
	): Promise<CompanyTimeSettings> => {
		return request<CompanyTimeSettings>(`/settings/company/${companyId}`, {
			method: "PUT",
			body: JSON.stringify(data),
		});
	},
};

// Holidays API
export const holidaysApi = {
	/**
	 * List public holidays for a year and region.
	 */
	list: (year: number, countryCode?: string): Promise<Holiday[]> => {
		const params = new URLSearchParams();
		params.set("year", String(year));
		if (countryCode) params.set("country_code", countryCode);
		return request<Holiday[]>(`/holidays?${params.toString()}`);
	},
};

// Reports API
export const reportsApi = {
	/**
	 * Get monthly report.
	 */
	getMonthly: (
		year: number,
		month: number,
		companyId?: Uuid,
	): Promise<MonthlyReportResponse> => {
		const params = new URLSearchParams();
		params.set("year", String(year));
		params.set("month", String(month));
		if (companyId) params.set("company_id", companyId);
		return request<MonthlyReportResponse>(
			`/reports/monthly?${params.toString()}`,
		);
	},
};

// Companies API (for fetching company list from main app)
const MAIN_API_BASE = "/api/v1";

async function mainRequest<T>(path: string): Promise<T> {
	const response = await fetch(`${MAIN_API_BASE}${path}`, {
		headers: { "Content-Type": "application/json" },
		credentials: "include",
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new ApiError(response.status, error.detail || "Request failed");
	}

	return response.json();
}

// Minimal Company interface for plugin use
export interface Company {
	id: string;
	name: string;
}

export const companiesApi = {
	list: (): Promise<Company[]> => {
		return mainRequest<Company[]>("/companies");
	},
};

// Submission response types
export interface SubmissionResponse {
	id: string;
	status: "pending" | "sent" | "failed";
	sent_to: string;
	period: string;
	entry_count: number;
}

export interface SubmissionListItem {
	id: string;
	company_id: string;
	period_start: string;
	period_end: string;
	period_type: string;
	submitted_at: string;
	sent_to_email: string;
	status: string;
	notes: string | null;
}

export interface SubmissionListResponse {
	total: number;
	submissions: SubmissionListItem[];
}

// Monthly Submission API
export const submissionsApi = {
	submit: (params: {
		companyId: Uuid;
		year: number;
		month: number;
		recipientEmail: string;
		notes?: string;
	}): Promise<SubmissionResponse> => {
		const searchParams = new URLSearchParams();
		searchParams.set("company_id", params.companyId);
		searchParams.set("year", String(params.year));
		searchParams.set("month", String(params.month));
		searchParams.set("recipient_email", params.recipientEmail);
		if (params.notes) searchParams.set("notes", params.notes);

		return request<SubmissionResponse>(
			`/submissions?${searchParams.toString()}`,
			{ method: "POST" },
		);
	},

	list: (params?: {
		companyId?: Uuid;
		skip?: number;
		limit?: number;
	}): Promise<SubmissionListResponse> => {
		const searchParams = new URLSearchParams();
		if (params?.companyId) searchParams.set("company_id", params.companyId);
		if (params?.skip !== undefined)
			searchParams.set("skip", String(params.skip));
		if (params?.limit !== undefined)
			searchParams.set("limit", String(params.limit));

		const query = searchParams.toString();
		return request<SubmissionListResponse>(
			`/submissions${query ? `?${query}` : ""}`,
		);
	},
};

// Utility functions
export function formatTime(timeStr: string | null): string {
	if (!timeStr) return "--:--";
	return timeStr;
}

export function formatHours(hours: number | null): string {
	if (hours === null) return "-";
	return `${hours.toFixed(1)}h`;
}

export function formatDate(dateStr: string): string {
	const date = new Date(dateStr);
	return date.toLocaleDateString("de-AT", {
		weekday: "short",
		day: "2-digit",
		month: "2-digit",
	});
}

export function getWeekStart(date: Date): Date {
	const d = new Date(date);
	const day = d.getDay();
	const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Monday as start
	d.setDate(diff);
	d.setHours(0, 0, 0, 0);
	return d;
}

export function getWeekEnd(date: Date): Date {
	const start = getWeekStart(date);
	const end = new Date(start);
	end.setDate(end.getDate() + 6);
	return end;
}

export function toISODateString(date: Date): string {
	// Use local timezone to avoid UTC conversion issues
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}
