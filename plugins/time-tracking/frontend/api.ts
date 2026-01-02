// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

/**
 * Time Tracking Plugin API Client
 *
 * API functions for communicating with the time-tracking backend endpoints.
 */

import type {
	CheckInOutResponse,
	CompanyTimeSettings,
	CompanyTimeSettingsCreate,
	CompanyTimeSettingsUpdate,
	Holiday,
	LeaveBalanceResponse,
	MonthlyReportSummary,
	TimeAllocation,
	TimeAllocationCreate,
	TimeRecord,
	TimeRecordCreate,
	TimeRecordListResponse,
	TimeRecordUpdate,
	TimeRecordWithWarnings,
	Uuid,
	WeekData,
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

// Time Records API
export const timeRecordsApi = {
	list: (params?: {
		company_id?: Uuid;
		start_date?: string;
		end_date?: string;
		day_type?: string;
	}): Promise<TimeRecord[]> => {
		const searchParams = new URLSearchParams();
		if (params?.company_id) searchParams.set("company_id", params.company_id);
		// Backend uses 'from' and 'to' query params
		if (params?.start_date) searchParams.set("from", params.start_date);
		if (params?.end_date) searchParams.set("to", params.end_date);
		if (params?.day_type) searchParams.set("day_type", params.day_type);

		const query = searchParams.toString();
		return request<TimeRecord[]>(`/records${query ? `?${query}` : ""}`);
	},

	get: (recordId: Uuid): Promise<TimeRecord> => {
		return request<TimeRecord>(`/records/${recordId}`);
	},

	create: (data: TimeRecordCreate): Promise<TimeRecordWithWarnings> => {
		return request<TimeRecordWithWarnings>("/records", {
			method: "POST",
			body: JSON.stringify(data),
		});
	},

	update: (
		recordId: Uuid,
		data: TimeRecordUpdate,
	): Promise<TimeRecordWithWarnings> => {
		return request<TimeRecordWithWarnings>(`/records/${recordId}`, {
			method: "PUT",
			body: JSON.stringify(data),
		});
	},

	delete: (recordId: Uuid): Promise<void> => {
		return request<void>(`/records/${recordId}`, {
			method: "DELETE",
		});
	},

	getToday: (companyId: Uuid): Promise<TimeRecord | null> => {
		return request<TimeRecord | null>(`/today?company_id=${companyId}`);
	},

	checkIn: (companyId: Uuid): Promise<CheckInOutResponse> => {
		return request<CheckInOutResponse>("/check-in", {
			method: "POST",
			body: JSON.stringify({
				company_id: companyId,
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			}),
		});
	},

	checkOut: (): Promise<CheckInOutResponse> => {
		return request<CheckInOutResponse>("/check-out", {
			method: "POST",
			body: JSON.stringify({
				timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
			}),
		});
	},

	lock: (recordId: Uuid): Promise<TimeRecord> => {
		return request<TimeRecord>(`/records/${recordId}/lock`, {
			method: "POST",
		});
	},

	unlock: (recordId: Uuid): Promise<TimeRecord> => {
		return request<TimeRecord>(`/records/${recordId}/unlock`, {
			method: "POST",
		});
	},
};

// Time Allocations API
export const allocationsApi = {
	list: (recordId: Uuid): Promise<TimeAllocation[]> => {
		return request<TimeAllocation[]>(`/records/${recordId}/allocations`);
	},

	create: (
		recordId: Uuid,
		data: TimeAllocationCreate,
	): Promise<TimeAllocation> => {
		return request<TimeAllocation>(`/records/${recordId}/allocations`, {
			method: "POST",
			body: JSON.stringify(data),
		});
	},

	update: (
		recordId: Uuid,
		allocationId: Uuid,
		data: Partial<TimeAllocationCreate>,
	): Promise<TimeAllocation> => {
		return request<TimeAllocation>(
			`/records/${recordId}/allocations/${allocationId}`,
			{
				method: "PUT",
				body: JSON.stringify(data),
			},
		);
	},

	delete: (recordId: Uuid, allocationId: Uuid): Promise<void> => {
		return request<void>(`/records/${recordId}/allocations/${allocationId}`, {
			method: "DELETE",
		});
	},
};

// Leave Balance API
export const leaveBalanceApi = {
	get: (year?: number): Promise<LeaveBalanceResponse> => {
		const params = new URLSearchParams();
		if (year) params.set("year", String(year));
		const query = params.toString();
		return request<LeaveBalanceResponse>(`/leave-balance${query ? `?${query}` : ""}`);
	},
};

// Company Settings API
export const companySettingsApi = {
	get: (companyId: Uuid): Promise<CompanyTimeSettings | null> => {
		return request<CompanyTimeSettings | null>(
			`/settings/company/${companyId}`,
		);
	},

	create: (
		companyId: Uuid,
		data: CompanyTimeSettingsCreate,
	): Promise<CompanyTimeSettings> => {
		return request<CompanyTimeSettings>(`/settings/company/${companyId}`, {
			method: "POST",
			body: JSON.stringify(data),
		});
	},

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
	list: (year: number, region?: string): Promise<Holiday[]> => {
		const params = new URLSearchParams();
		params.set("year", String(year));
		if (region) params.set("region", region);
		return request<Holiday[]>(`/holidays?${params.toString()}`);
	},
};

// Reports API
export const reportsApi = {
	getMonthly: (
		companyId: Uuid,
		year: number,
		month: number,
	): Promise<MonthlyReportSummary> => {
		return request<MonthlyReportSummary>(
			`/reports/monthly?company_id=${companyId}&year=${year}&month=${month}`,
		);
	},

	getWeek: (companyId: Uuid, startDate: string): Promise<WeekData> => {
		return request<WeekData>(
			`/reports/week?company_id=${companyId}&start_date=${startDate}`,
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
	record_count: number;
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
