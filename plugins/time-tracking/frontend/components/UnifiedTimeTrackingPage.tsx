// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useMemo, useState } from "react";
import { companiesApi, holidaysApi, timeRecordsApi, toISODateString } from "../api";
import type {
	CompanyInfo,
	ComplianceWarning,
	Holiday,
	TimeRecord,
	TimeRecordCreate,
	TimeRecordUpdate,
	TimeRecordWithWarnings,
} from "../types";
import { COMPANY_COLORS } from "../types";
import { LeaveBalanceCard } from "./LeaveBalanceCard";
import { MonthCalendarView } from "./MonthCalendarView";
import { MonthlySubmissionPanel } from "./MonthlySubmissionPanel";
import { SubmissionCard } from "./SubmissionCard";
import { TableView } from "./TableView";
import { TimeRecordForm } from "./TimeRecordForm";
import { TodayStatusBar } from "./TodayStatusBar";

type ViewMode = "calendar" | "table";

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
	const [records, setRecords] = useState<TimeRecord[]>([]);
	const [companies, setCompanies] = useState<CompanyInfo[]>([]);
	const [visibleCompanyIds, setVisibleCompanyIds] = useState<Set<string>>(
		new Set(),
	);
	const [selectedRecord, setSelectedRecord] = useState<TimeRecord | null>(null);
	const [selectedDate, setSelectedDate] = useState<string | null>(null);
	const [formWarnings, setFormWarnings] = useState<ComplianceWarning[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isSaving, setIsSaving] = useState(false);
	const [showSubmissionPanel, setShowSubmissionPanel] = useState(false);
	const [holidays, setHolidays] = useState<Holiday[]>([]);

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
			console.error("Failed to load companies:", err);
		}
	}, []);

	// Fetch records for the current month (no company_id filter)
	const loadRecords = useCallback(async () => {
		setIsLoading(true);
		try {
			const monthStart = getMonthStart(currentDate);
			const monthEnd = getMonthEnd(currentDate);

			// API returns array directly
			const records = await timeRecordsApi.list({
				start_date: toISODateString(monthStart),
				end_date: toISODateString(monthEnd),
			});
			setRecords(records);
		} catch (err) {
			console.error("Failed to load records:", err);
		} finally {
			setIsLoading(false);
		}
	}, [currentDate]);

	useEffect(() => {
		loadCompanies();
	}, [loadCompanies]);

	useEffect(() => {
		loadRecords();
	}, [loadRecords]);

	// Fetch holidays for the current year
	const loadHolidays = useCallback(async () => {
		try {
			const year = currentDate.getFullYear();
			const data = await holidaysApi.list(year);
			setHolidays(data);
		} catch (err) {
			console.error("Failed to load holidays:", err);
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

	// Filter records by visible companies
	const visibleRecords = useMemo(() => {
		return records.filter((record) => visibleCompanyIds.has(record.company_id));
	}, [records, visibleCompanyIds]);

	// Get companies that have records in the current month
	const companiesWithRecords = useMemo(() => {
		const companyIdsWithRecords = new Set(records.map((r) => r.company_id));
		return companies.filter((c) => companyIdsWithRecords.has(c.id));
	}, [records, companies]);

	// Group records by date for calendar display
	const recordsByDate = useMemo(() => {
		const map = new Map<string, TimeRecord[]>();
		for (const record of visibleRecords) {
			const existing = map.get(record.date) || [];
			map.set(record.date, [...existing, record]);
		}
		return map;
	}, [visibleRecords]);

	// Detect overlaps: multiple records on the same date with overlapping times
	const overlappingRecordIds = useMemo(() => {
		const overlaps = new Set<string>();

		for (const [, dateRecords] of recordsByDate) {
			if (dateRecords.length < 2) continue;

			// Check each pair for time overlap
			for (let i = 0; i < dateRecords.length; i++) {
				for (let j = i + 1; j < dateRecords.length; j++) {
					const r1 = dateRecords[i];
					const r2 = dateRecords[j];

					// Only check work days with actual times
					if (
						r1.day_type === "work" &&
						r2.day_type === "work" &&
						r1.check_in &&
						r1.check_out &&
						r2.check_in &&
						r2.check_out
					) {
						if (
							timesOverlap(r1.check_in, r1.check_out, r2.check_in, r2.check_out)
						) {
							overlaps.add(r1.id);
							overlaps.add(r2.id);
						}
					}
				}
			}
		}

		return overlaps;
	}, [recordsByDate]);

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

	// Handle clicking on a specific record to edit
	const handleRecordClick = (record: TimeRecord) => {
		// Don't allow editing public holidays
		if (record.day_type === "public_holiday") return;
		setSelectedRecord(record);
		setSelectedDate(record.date);
		setFormWarnings([]);
	};

	// Handle clicking on a date to add new record
	const handleDateClick = (date: string) => {
		setSelectedDate(date);
		setSelectedRecord(null);
		setFormWarnings([]);
	};

	// Handle form submission
	const handleFormSubmit = async (
		data: TimeRecordCreate | TimeRecordUpdate,
	) => {
		setIsSaving(true);
		try {
			let result: TimeRecordWithWarnings;
			if (selectedRecord) {
				result = await timeRecordsApi.update(
					selectedRecord.id,
					data as TimeRecordUpdate,
				);
			} else {
				result = await timeRecordsApi.create(data as TimeRecordCreate);
			}

			const warnings = result.warnings || [];
			setFormWarnings(warnings);

			// If no errors, close the form and reload
			if (!warnings.some((w) => w.level === "error")) {
				setSelectedDate(null);
				setSelectedRecord(null);
				setFormWarnings([]);
				await loadRecords();
			}
		} finally {
			setIsSaving(false);
		}
	};

	const handleFormCancel = () => {
		setSelectedDate(null);
		setSelectedRecord(null);
		setFormWarnings([]);
	};

	// Handle record deletion
	const handleDeleteRecord = async (record: TimeRecord) => {
		if (!window.confirm("Are you sure you want to delete this time record?")) {
			return;
		}
		try {
			await timeRecordsApi.delete(record.id);
			await loadRecords();
		} catch (err) {
			console.error("Failed to delete record:", err);
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
	const getCompanyColor = (companyId: string): string => {
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

			{/* Today's status bar with check-in/out */}
			<TodayStatusBar
				companies={companies}
				companiesWithRecords={companiesWithRecords}
				records={records}
				holidays={new Set(holidaysByDate.keys())}
				currentDate={currentDate}
				onStatusChange={loadRecords}
			/>

			{/* Two-column layout: Main content + Sidebar */}
			<div className="flex gap-6">
				{/* Main content area */}
				<div className="flex-1 min-w-0 space-y-4">
						{/* Controls row: company filters on left, month nav + view toggle on right */}
					<div className="flex items-center justify-between flex-wrap gap-4">
						{/* Company filter toggles - only show companies with records this month */}
						<div className="flex flex-wrap gap-2">
							{companiesWithRecords.map((company) => {
								const isVisible = visibleCompanyIds.has(company.id);
								return (
									<button
										key={company.id}
										type="button"
										onClick={() => toggleCompany(company.id)}
										className={`
											px-3 py-1.5 text-sm font-medium rounded-full border-2 transition-colors
											${
												isVisible
													? "text-white border-transparent"
													: "bg-white text-gray-500 border-gray-300 hover:border-gray-400"
											}
										`}
										style={
											isVisible
												? {
														backgroundColor: company.color,
														borderColor: company.color,
													}
												: undefined
										}
									>
										{company.name}
									</button>
								);
							})}
						</div>

						{/* Month navigation and view toggle */}
						<div className="flex items-center gap-2">
							<button
								type="button"
								onClick={goToPreviousMonth}
								className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
								aria-label="Previous month"
							>
								<svg
									className="w-5 h-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
									aria-hidden="true"
								>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={2}
										d="M15 19l-7-7 7-7"
									/>
								</svg>
							</button>

							<button
								type="button"
								onClick={goToToday}
								className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
							>
								Today
							</button>

							<span className="min-w-[140px] text-center text-lg font-semibold text-gray-900">
								{monthYearDisplay}
							</span>

							<button
								type="button"
								onClick={goToNextMonth}
								className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
								aria-label="Next month"
							>
								<svg
									className="w-5 h-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
									aria-hidden="true"
								>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={2}
										d="M9 5l7 7-7 7"
									/>
								</svg>
							</button>

							{/* View toggle */}
							<div className="ml-2 flex rounded-md overflow-hidden border border-gray-300">
								<button
									type="button"
									onClick={() => setViewMode("calendar")}
									className={`px-3 py-1.5 text-sm font-medium ${
										viewMode === "calendar"
											? "bg-blue-600 text-white"
											: "bg-white text-gray-700 hover:bg-gray-50"
									}`}
								>
									Calendar
								</button>
								<button
									type="button"
									onClick={() => setViewMode("table")}
									className={`px-3 py-1.5 text-sm font-medium border-l border-gray-300 ${
										viewMode === "table"
											? "bg-blue-600 text-white"
											: "bg-white text-gray-700 hover:bg-gray-50"
									}`}
								>
									Table
								</button>
							</div>

							{/* Add Entry button */}
							<button
								type="button"
								onClick={() => handleDateClick(toISODateString(new Date()))}
								className="ml-2 px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
							>
								Add Entry
							</button>
						</div>
					</div>

					{/* View: Calendar or Table */}
					{viewMode === "calendar" ? (
						<MonthCalendarView
							currentDate={currentDate}
							recordsByDate={recordsByDate}
							overlappingRecordIds={overlappingRecordIds}
							holidaysByDate={holidaysByDate}
							getCompanyColor={getCompanyColor}
							onRecordClick={handleRecordClick}
							onDateClick={handleDateClick}
							isLoading={isLoading}
						/>
					) : (
						<TableView
							records={visibleRecords}
							overlappingRecordIds={overlappingRecordIds}
							companies={companies}
							getCompanyColor={getCompanyColor}
							onRecordClick={handleRecordClick}
							onDeleteRecord={handleDeleteRecord}
							isLoading={isLoading}
						/>
					)}

					{/* Keyboard shortcut help */}
					<div className="text-xs text-gray-400 text-center">
						Click on an entry to edit, or click on an empty day to add a new record.
					</div>
				</div>

				{/* Sidebar */}
				<div className="w-72 flex-shrink-0 space-y-4">
					<LeaveBalanceCard currentDate={currentDate} />
					<SubmissionCard
						companies={companies}
						currentDate={currentDate}
						onOpenFullPanel={() => setShowSubmissionPanel(true)}
					/>
				</div>
			</div>

			{/* Time record form modal */}
			{selectedDate && (
				<div className="fixed inset-0 z-50 overflow-y-auto">
					<div className="flex min-h-screen items-center justify-center p-4">
						{/* Backdrop */}
						<button
							type="button"
							className="fixed inset-0 bg-black bg-opacity-25 cursor-default"
							onClick={handleFormCancel}
							onKeyDown={(e) => e.key === "Escape" && handleFormCancel()}
							aria-label="Close modal"
						/>

						{/* Modal */}
						<div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
							<h2 className="text-lg font-medium text-gray-900 mb-4">
								{selectedRecord ? "Edit Time Record" : "New Time Record"}
							</h2>
							<TimeRecordForm
								record={selectedRecord}
								companyId={selectedRecord?.company_id || companies[0]?.id || ""}
								date={selectedDate}
								onSubmit={handleFormSubmit}
								onCancel={handleFormCancel}
								warnings={formWarnings}
								isLoading={isSaving}
								companies={companies}
								preselectedCompanyId={selectedRecord?.company_id}
							/>
						</div>
					</div>
				</div>
			)}

			{/* Submission Panel (Slide-out) */}
			{showSubmissionPanel && (
				<div className="fixed inset-0 z-50 overflow-hidden">
					{/* Backdrop */}
					<button
						type="button"
						className="fixed inset-0 bg-black bg-opacity-25 cursor-default"
						onClick={() => setShowSubmissionPanel(false)}
						onKeyDown={(e) =>
							e.key === "Escape" && setShowSubmissionPanel(false)
						}
						aria-label="Close submission panel"
					/>

					{/* Panel */}
					<div className="fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-xl overflow-y-auto">
						<div className="p-4 border-b border-gray-200 flex items-center justify-between">
							<h2 className="text-lg font-semibold text-gray-900">
								Submit Timesheet
							</h2>
							<button
								type="button"
								onClick={() => setShowSubmissionPanel(false)}
								className="p-2 text-gray-400 hover:text-gray-600 rounded-md"
								aria-label="Close"
							>
								<svg
									className="w-5 h-5"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
									aria-hidden="true"
								>
									<title>Close</title>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={2}
										d="M6 18L18 6M6 6l12 12"
									/>
								</svg>
							</button>
						</div>
						<div className="p-4">
							<MonthlySubmissionPanel
								companies={companies}
								currentDate={currentDate}
							/>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

/**
 * Check if two time ranges overlap.
 * Times are in HH:MM format.
 */
function timesOverlap(
	start1: string,
	end1: string,
	start2: string,
	end2: string,
): boolean {
	const toMinutes = (time: string): number => {
		const [h, m] = time.split(":").map(Number);
		return h * 60 + m;
	};

	let start1Mins = toMinutes(start1);
	let end1Mins = toMinutes(end1);
	let start2Mins = toMinutes(start2);
	let end2Mins = toMinutes(end2);

	// Handle overnight shifts
	const range1Overnight = end1Mins < start1Mins;
	const range2Overnight = end2Mins < start2Mins;

	if (range1Overnight) end1Mins += 24 * 60;
	if (range2Overnight) end2Mins += 24 * 60;

	// Adjust for overnight comparisons
	if (range1Overnight && !range2Overnight) {
		const originalEnd1 = toMinutes(end1);
		if (start2Mins < originalEnd1) {
			start2Mins += 24 * 60;
			end2Mins += 24 * 60;
		}
	}

	if (range2Overnight && !range1Overnight) {
		const originalEnd2 = toMinutes(end2);
		if (start1Mins < originalEnd2) {
			start1Mins += 24 * 60;
			end1Mins += 24 * 60;
		}
	}

	return start1Mins < end2Mins && start2Mins < end1Mins;
}
