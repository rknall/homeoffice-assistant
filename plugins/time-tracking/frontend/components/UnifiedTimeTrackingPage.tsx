// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useMemo, useState } from "react";
import {
	companiesApi,
	errorMessage,
	holidaysApi,
	timeEntriesApi,
	toISODateString,
} from "../api";
import { confirmAction } from "../host";
import type {
	CompanyInfo,
	ComplianceWarning,
	Holiday,
	TimeEntry,
	TimeEntryCreate,
	TimeEntryUpdate,
} from "../types";
import { COMPANY_COLORS } from "../types";
import { EntryModal } from "./EntryModal";
import { findOverlappingEntryIds, groupEntriesByDate } from "./entryGrouping";
import { LeaveBalanceCard } from "./LeaveBalanceCard";
import { MonthCalendarView } from "./MonthCalendarView";
import { PageControls, type ViewMode } from "./PageControls";
import { TableView } from "./TableView";
import { TodayStatusBar } from "./TodayStatusBar";

// Get month boundaries (defined outside component to avoid useCallback dependencies)
function getMonthStart(date: Date): Date {
	return new Date(date.getFullYear(), date.getMonth(), 1);
}

function getMonthEnd(date: Date): Date {
	return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

/**
 * UnifiedTimeTrackingPage - Multi-company time tracking view
 *
 * Displays a monthly calendar with time entries from all companies,
 * with company toggle filters and overlap detection.
 */
export function UnifiedTimeTrackingPage() {
	const [viewMode, setViewMode] = useState<ViewMode>("calendar");
	const [currentDate, setCurrentDate] = useState(new Date());
	const [entries, setEntries] = useState<TimeEntry[]>([]);
	const [companies, setCompanies] = useState<CompanyInfo[]>([]);
	const [visibleCompanyIds, setVisibleCompanyIds] = useState<Set<string>>(
		new Set(),
	);
	const [selectedEntry, setSelectedEntry] = useState<TimeEntry | null>(null);
	const [selectedDate, setSelectedDate] = useState<string | null>(null);
	const [formWarnings, setFormWarnings] = useState<ComplianceWarning[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isSaving, setIsSaving] = useState(false);
	const [holidays, setHolidays] = useState<Holiday[]>([]);
	const [error, setError] = useState<string | null>(null);

	// Fetch companies on mount
	const loadCompanies = useCallback(async () => {
		try {
			const data = await companiesApi.list();
			// Assign colors to companies cyclically
			const companiesWithColors: CompanyInfo[] = data.map((company, index) => ({
				id: company.id,
				name: company.name,
				color: COMPANY_COLORS[index % COMPANY_COLORS.length],
			}));
			setCompanies(companiesWithColors);
			// All companies visible by default
			setVisibleCompanyIds(new Set(companiesWithColors.map((c) => c.id)));
		} catch (err) {
			setError(errorMessage(err, "Failed to load companies"));
		}
	}, []);

	// Fetch entries for the current month (no company_id filter)
	const loadEntries = useCallback(async () => {
		setIsLoading(true);
		try {
			const monthStart = getMonthStart(currentDate);
			const monthEnd = getMonthEnd(currentDate);

			// API returns array directly
			const entriesData = await timeEntriesApi.list({
				start_date: toISODateString(monthStart),
				end_date: toISODateString(monthEnd),
			});
			setEntries(entriesData);
		} catch (err) {
			setError(errorMessage(err, "Failed to load entries"));
		} finally {
			setIsLoading(false);
		}
	}, [currentDate]);

	useEffect(() => {
		loadCompanies();
	}, [loadCompanies]);

	useEffect(() => {
		loadEntries();
	}, [loadEntries]);

	// Fetch holidays for the current year
	const loadHolidays = useCallback(async () => {
		try {
			const year = currentDate.getFullYear();
			const data = await holidaysApi.list(year);
			setHolidays(data);
		} catch (err) {
			setError(errorMessage(err, "Failed to load holidays"));
		}
	}, [currentDate]);

	useEffect(() => {
		loadHolidays();
	}, [loadHolidays]);

	// Create a map of date strings to holiday names for quick lookup
	const holidaysByDate = useMemo(() => {
		const map = new Map<string, string>();
		for (const holiday of holidays) {
			map.set(holiday.date, holiday.name);
		}
		return map;
	}, [holidays]);

	// Filter entries by visible companies
	const visibleEntries = useMemo(() => {
		return entries.filter(
			(entry) =>
				entry.company_id === null || visibleCompanyIds.has(entry.company_id),
		);
	}, [entries, visibleCompanyIds]);

	// Get companies that have entries in the current month
	const companiesWithEntries = useMemo(() => {
		const companyIdsWithEntries = new Set(
			entries.filter((e) => e.company_id).map((e) => e.company_id as string),
		);
		return companies.filter((c) => companyIdsWithEntries.has(c.id));
	}, [entries, companies]);


	// Group entries by date for calendar display and detect overlapping times
	const entriesByDate = useMemo(
		() => groupEntriesByDate(visibleEntries),
		[visibleEntries],
	);
	const overlappingEntryIds = useMemo(
		() => findOverlappingEntryIds(entriesByDate),
		[entriesByDate],
	);

	// Toggle company visibility
	const toggleCompany = (companyId: string) => {
		setVisibleCompanyIds((prev) => {
			const next = new Set(prev);
			if (next.has(companyId)) {
				next.delete(companyId);
			} else {
				next.add(companyId);
			}
			return next;
		});
	};

	// Handle clicking on a specific entry to edit
	const handleEntryClick = (entry: TimeEntry) => {
		// Don't allow editing public holidays
		if (entry.entry_type === "public_holiday") return;
		setSelectedEntry(entry);
		setSelectedDate(entry.date);
		setFormWarnings([]);
	};

	// Handle clicking on a date to add new entry
	const handleDateClick = (date: string) => {
		setSelectedDate(date);
		setSelectedEntry(null);
		setFormWarnings([]);
	};

	// Handle form submission. Errors propagate to the form, which shows them.
	const handleFormSubmit = async (data: TimeEntryCreate | TimeEntryUpdate) => {
		setIsSaving(true);
		try {
			if (selectedEntry) {
				await timeEntriesApi.update(selectedEntry.id, data as TimeEntryUpdate);
			} else {
				await timeEntriesApi.create(data as TimeEntryCreate);
			}

			// Close the form and reload
			setSelectedDate(null);
			setSelectedEntry(null);
			setFormWarnings([]);
			await loadEntries();
		} finally {
			setIsSaving(false);
		}
	};

	const handleFormCancel = () => {
		setSelectedDate(null);
		setSelectedEntry(null);
		setFormWarnings([]);
	};

	// Handle entry deletion
	const handleDeleteEntry = async (entry: TimeEntry) => {
		const confirmed = await confirmAction({
			title: "Delete time entry",
			message: "Are you sure you want to delete this time entry?",
			confirmLabel: "Delete",
		});
		if (!confirmed) {
			return;
		}
		try {
			await timeEntriesApi.delete(entry.id);
			await loadEntries();
		} catch (err) {
			setError(errorMessage(err, "Failed to delete entry"));
		}
	};

	// Navigate to previous/next month
	const goToPreviousMonth = () => {
		setCurrentDate(
			(prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1),
		);
	};

	const goToNextMonth = () => {
		setCurrentDate(
			(prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1),
		);
	};

	const goToToday = () => {
		setCurrentDate(new Date());
	};

	// Get company color by ID
	const getCompanyColor = (companyId: string | null): string => {
		if (!companyId) return "#6B7280"; // gray-500 for no company
		const company = companies.find((c) => c.id === companyId);
		return company?.color || COMPANY_COLORS[0];
	};

	// Month/year display
	const monthYearDisplay = currentDate.toLocaleDateString("en-US", {
		month: "long",
		year: "numeric",
	});

	return (
		<div className="space-y-4">
			{/* Title */}
			<div>
				<h1 className="text-2xl font-bold text-gray-900">Time Tracking</h1>
				<p className="text-sm text-gray-500">All Companies</p>
			</div>

			{error && (
				<div
					role="alert"
					className="p-3 rounded-md bg-red-50 border border-red-200 flex items-start justify-between gap-4"
				>
					<p className="text-sm text-red-700">{error}</p>
					<button
						type="button"
						onClick={() => setError(null)}
						className="text-sm text-red-700 hover:text-red-900"
					>
						Dismiss
					</button>
				</div>
			)}

			{/* Today's status bar with check-in/out */}
			<TodayStatusBar
				companies={companies}
				entries={entries}
				holidays={new Set(holidaysByDate.keys())}
				currentDate={currentDate}
				onStatusChange={loadEntries}
				onError={setError}
			/>

			{/* Two-column layout: Main content + Sidebar */}
			<div className="flex gap-6">
				{/* Main content area */}
				<div className="flex-1 min-w-0 space-y-4">
					<PageControls
						companiesWithEntries={companiesWithEntries}
						visibleCompanyIds={visibleCompanyIds}
						onToggleCompany={toggleCompany}
						monthYearDisplay={monthYearDisplay}
						onPreviousMonth={goToPreviousMonth}
						onNextMonth={goToNextMonth}
						onToday={goToToday}
						viewMode={viewMode}
						onViewModeChange={setViewMode}
						onAddEntry={() => handleDateClick(toISODateString(new Date()))}
					/>

					{/* View: Calendar or Table */}
					{viewMode === "calendar" ? (
						<MonthCalendarView
							currentDate={currentDate}
							entriesByDate={entriesByDate}
							overlappingEntryIds={overlappingEntryIds}
							holidaysByDate={holidaysByDate}
							getCompanyColor={getCompanyColor}
							onEntryClick={handleEntryClick}
							onDateClick={handleDateClick}
							isLoading={isLoading}
						/>
					) : (
						<TableView
							entries={visibleEntries}
							overlappingEntryIds={overlappingEntryIds}
							companies={companies}
							getCompanyColor={getCompanyColor}
							onEntryClick={handleEntryClick}
							onDeleteEntry={handleDeleteEntry}
							isLoading={isLoading}
						/>
					)}

					{/* Keyboard shortcut help */}
					<div className="text-xs text-gray-400 text-center">
						Click on an entry to edit, or click on an empty day to add a new
						entry.
					</div>
				</div>

				{/* Sidebar */}
				<div className="w-72 flex-shrink-0 space-y-4">
					<LeaveBalanceCard currentDate={currentDate} />
				</div>
			</div>

			{/* Time entry form modal */}
			{selectedDate && (
				<EntryModal
					selectedDate={selectedDate}
					selectedEntry={selectedEntry}
					companies={companies}
					warnings={formWarnings}
					isSaving={isSaving}
					onSubmit={handleFormSubmit}
					onCancel={handleFormCancel}
				/>
			)}
		</div>
	);
}
