// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useMemo, useState } from "react";
import { timeEntriesApi, toISODateString } from "../api";
import type { CompanyInfo, TimeEntry } from "../types";

interface TodayStatusBarProps {
	companies: CompanyInfo[]; // All companies (for check-in)
	companiesWithRecords: CompanyInfo[]; // Only companies with entries this month
	entries: TimeEntry[]; // All entries for the current month
	holidays: Set<string>; // Set of holiday date strings (YYYY-MM-DD)
	currentDate: Date;
	onStatusChange?: () => void;
}

/**
 * Calculate the number of base working days (Mon-Fri, excluding holidays) in a given month
 */
function getBaseWorkingDaysInMonth(
	year: number,
	month: number,
	holidays: Set<string>,
): number {
	const firstDay = new Date(year, month, 1);
	const lastDay = new Date(year, month + 1, 0);
	let workingDays = 0;

	for (let d = new Date(firstDay); d <= lastDay; d.setDate(d.getDate() + 1)) {
		const dayOfWeek = d.getDay();
		const dateStr = toISODateString(d);
		// Count as working day if it's a weekday AND not a holiday
		if (dayOfWeek !== 0 && dayOfWeek !== 6 && !holidays.has(dateStr)) {
			workingDays++;
		}
	}

	return workingDays;
}

/**
 * Count effective leave days applying priority rules:
 * 1. National Holiday > 2. Weekend > 3. Sickness > 4. Vacation
 */
function countEffectiveLeaveDays(
	entries: TimeEntry[],
	holidays: Set<string>,
	year: number,
	month: number,
): { sickDays: number; vacationDays: number } {
	const monthStart = new Date(year, month, 1);
	const monthEnd = new Date(year, month + 1, 0);

	// Collect all sick and vacation days
	const sickDates = new Set<string>();
	const vacationDates = new Set<string>();
	const halfVacationDates = new Set<string>();

	for (const entry of entries) {
		if (entry.entry_type !== "sick" && entry.entry_type !== "vacation") {
			continue;
		}

		// Determine date range
		const startDate = new Date(entry.date);
		const endDate = entry.end_date ? new Date(entry.end_date) : startDate;

		// Iterate through each day in the entry's range
		for (
			let d = new Date(startDate);
			d <= endDate;
			d.setDate(d.getDate() + 1)
		) {
			// Only count days within the target month
			if (d >= monthStart && d <= monthEnd) {
				const dateStr = toISODateString(d);
				if (entry.entry_type === "sick") {
					sickDates.add(dateStr);
				} else if (entry.entry_type === "vacation") {
					if (entry.is_half_day) {
						halfVacationDates.add(dateStr);
					} else {
						vacationDates.add(dateStr);
					}
				}
			}
		}
	}

	// Apply priority rules
	let effectiveSick = 0;
	let effectiveVacation = 0;

	// Process sick days
	for (const dateStr of sickDates) {
		const d = new Date(dateStr);
		const dayOfWeek = d.getDay();
		// Skip weekends
		if (dayOfWeek === 0 || dayOfWeek === 6) continue;
		// Skip holidays
		if (holidays.has(dateStr)) continue;
		effectiveSick += 1;
	}

	// Process full vacation days (skip if sick day exists)
	for (const dateStr of vacationDates) {
		const d = new Date(dateStr);
		const dayOfWeek = d.getDay();
		if (dayOfWeek === 0 || dayOfWeek === 6) continue;
		if (holidays.has(dateStr)) continue;
		if (sickDates.has(dateStr)) continue;
		effectiveVacation += 1;
	}

	// Process half vacation days (skip if sick or full vacation)
	for (const dateStr of halfVacationDates) {
		const d = new Date(dateStr);
		const dayOfWeek = d.getDay();
		if (dayOfWeek === 0 || dayOfWeek === 6) continue;
		if (holidays.has(dateStr)) continue;
		if (sickDates.has(dateStr)) continue;
		if (vacationDates.has(dateStr)) continue;
		effectiveVacation += 0.5;
	}

	return { sickDays: effectiveSick, vacationDays: effectiveVacation };
}

/**
 * Calculate break minutes based on gross hours (Austrian labor law)
 */
function calculateBreakMinutes(grossHours: number): number {
	if (grossHours > 6) return 30;
	return 0;
}

/**
 * TodayStatusBar - Shows today's check-in status and monthly stats
 */
export function TodayStatusBar({
	companies,
	companiesWithRecords,
	entries,
	holidays,
	currentDate,
	onStatusChange,
}: TodayStatusBarProps) {
	const [todayEntries, setTodayEntries] = useState<TimeEntry[]>([]);
	const [elapsedTime, setElapsedTime] = useState<string>("");
	const [isLoading, setIsLoading] = useState(false);
	const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

	// Initialize selectedCompanyId when companies change
	useEffect(() => {
		if (companies.length > 0 && !selectedCompanyId) {
			setSelectedCompanyId(companies[0].id);
		}
	}, [companies, selectedCompanyId]);

	// Find the active entry (is_open = checked in but not checked out)
	const activeEntry = todayEntries.find(
		(e) => e.is_open && e.entry_type === "work",
	);

	// Calculate OVERALL monthly stats from entries
	const monthlyStats = useMemo(() => {
		const year = currentDate.getFullYear();
		const month = currentDate.getMonth();

		// Base working days (Mon-Fri, excluding public holidays)
		const baseWorkDays = getBaseWorkingDaysInMonth(year, month, holidays);

		// Count effective leave days (applying priority rules)
		const effectiveLeave = countEffectiveLeaveDays(entries, holidays, year, month);

		// Expected work days = base - effective leave
		const expectedWorkDays = baseWorkDays - effectiveLeave.sickDays - effectiveLeave.vacationDays;
		const expectedHours = expectedWorkDays * 8;

		// Count unique work days (days with work entries)
		const workDays = new Set<string>();
		let totalGrossMinutes = 0;
		let totalBreakMinutes = 0;

		for (const entry of entries) {
			if (entry.entry_type === "work" && entry.gross_hours !== null) {
				workDays.add(entry.date);
				totalGrossMinutes += entry.gross_hours * 60;
			}
		}

		// Calculate breaks per day (aggregate gross hours per day first)
		const dailyGrossHours = new Map<string, number>();
		for (const entry of entries) {
			if (entry.entry_type === "work" && entry.gross_hours !== null) {
				const current = dailyGrossHours.get(entry.date) || 0;
				dailyGrossHours.set(entry.date, current + entry.gross_hours);
			}
		}
		for (const [, grossHours] of dailyGrossHours) {
			totalBreakMinutes += calculateBreakMinutes(grossHours);
		}

		const actualWorkDays = workDays.size;
		const actualNetHours = (totalGrossMinutes - totalBreakMinutes) / 60;

		// Calculate expected work days up to today (not the whole month)
		const today = new Date();
		const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;

		let expectedWorkDaysSoFar = expectedWorkDays;
		if (isCurrentMonth) {
			// Count workdays from start of month up to today
			const monthStart = new Date(year, month, 1);
			let workdayCount = 0;
			const currentDay = new Date(monthStart);

			while (currentDay <= today) {
				const dayOfWeek = currentDay.getDay();
				const dateStr = currentDay.toISOString().split("T")[0];
				const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
				const isHoliday = holidays.has(dateStr);

				// Check if this day has leave (vacation or sick)
				const hasLeave = entries.some(e => {
					if (e.entry_type !== "vacation" && e.entry_type !== "sick") return false;
					const entryDate = new Date(e.date);
					const endDate = e.end_date ? new Date(e.end_date) : entryDate;
					return currentDay >= entryDate && currentDay <= endDate;
				});

				if (!isWeekend && !isHoliday && !hasLeave) {
					workdayCount++;
				}
				currentDay.setDate(currentDay.getDate() + 1);
			}
			expectedWorkDaysSoFar = workdayCount;
		}

		const expectedHoursSoFar = expectedWorkDaysSoFar * 8;

		// Comp time: actual hours - expected hours so far (can be negative)
		const compTime = actualNetHours - expectedHoursSoFar;

		return {
			actualWorkDays,
			expectedWorkDays,
			expectedWorkDaysSoFar,
			actualHours: actualNetHours,
			expectedHours,
			expectedHoursSoFar,
			compTime,
		};
	}, [entries, currentDate, holidays]);

	// Load today's entries
	const loadTodayStatus = useCallback(async () => {
		if (companies.length === 0) return;

		try {
			const todayData = await timeEntriesApi.getToday();
			setTodayEntries(todayData);
		} catch (err) {
			console.error("Failed to load today status:", err);
		}
	}, [companies]);

	useEffect(() => {
		loadTodayStatus();
	}, [loadTodayStatus]);

	// Update elapsed time every minute
	useEffect(() => {
		if (!activeEntry?.check_in) {
			setElapsedTime("");
			return;
		}

		const updateElapsed = () => {
			const [hours, minutes] = activeEntry.check_in!.split(":").map(Number);
			const checkInTime = new Date();
			checkInTime.setHours(hours, minutes, 0, 0);

			const now = new Date();
			const diffMs = now.getTime() - checkInTime.getTime();
			const diffMins = Math.floor(diffMs / 60000);

			if (diffMins < 0) {
				setElapsedTime("--:--");
				return;
			}

			const h = Math.floor(diffMins / 60);
			const m = diffMins % 60;
			setElapsedTime(`${h}h ${m.toString().padStart(2, "0")}m`);
		};

		updateElapsed();
		const interval = setInterval(updateElapsed, 60000);
		return () => clearInterval(interval);
	}, [activeEntry]);

	// Handle check-in
	const handleCheckIn = async () => {
		const companyToUse = selectedCompanyId || companies[0]?.id;
		if (!companyToUse) return;

		setIsLoading(true);
		try {
			await timeEntriesApi.checkIn({ company_id: companyToUse });
			await loadTodayStatus();
			onStatusChange?.();
		} catch (err) {
			console.error("Failed to check in:", err);
		} finally {
			setIsLoading(false);
		}
	};

	// Handle check-out
	const handleCheckOut = async () => {
		if (!activeEntry) return;

		setIsLoading(true);
		try {
			await timeEntriesApi.checkOut();
			await loadTodayStatus();
			onStatusChange?.();
		} catch (err) {
			console.error("Failed to check out:", err);
		} finally {
			setIsLoading(false);
		}
	};

	// Get company name for display
	const getCompanyName = (companyId: string | null): string => {
		if (!companyId) return "Unknown";
		const company = companies.find((c) => c.id === companyId);
		return company?.name || "Unknown";
	};

	// Get company color
	const getCompanyColor = (companyId: string | null): string => {
		if (!companyId) return "#3B82F6";
		const company = companies.find((c) => c.id === companyId);
		return company?.color || "#3B82F6";
	};

	// Format hours for display (handles negative values)
	const formatHours = (hours: number): string => {
		const absHours = Math.abs(hours);
		const h = Math.floor(absHours);
		const m = Math.round((absHours - h) * 60);
		const sign = hours < 0 ? "-" : "";
		if (m === 0) return `${sign}${h}h`;
		return `${sign}${h}h ${m}m`;
	};

	// Count completed entries for today
	const completedTodayCount = todayEntries.filter(
		(e) => !e.is_open && e.entry_type === "work",
	).length;

	return (
		<div className="bg-white rounded-lg shadow p-4">
			<div className="flex items-center justify-between gap-6 flex-wrap">
				{/* Today's status */}
				<div className="flex items-center gap-4">
					{activeEntry ? (
						<>
							{/* Pulsing green indicator */}
							<div className="relative">
								<div className="w-3 h-3 bg-green-500 rounded-full" />
								<div className="absolute inset-0 w-3 h-3 bg-green-500 rounded-full animate-ping opacity-75" />
							</div>
							<div>
								<div className="text-sm font-medium text-gray-900">
									Checked in at{" "}
									<span className="font-semibold">
										{activeEntry.check_in?.substring(0, 5) || "--:--"}
									</span>
									{elapsedTime && (
										<span className="text-gray-500 ml-2">({elapsedTime})</span>
									)}
								</div>
								<div className="text-xs text-gray-500 mt-1">
									<span
										className="inline-block px-2 py-0.5 rounded text-white text-xs"
										style={{
											backgroundColor: getCompanyColor(activeEntry.company_id),
										}}
									>
										{getCompanyName(activeEntry.company_id)}
									</span>
								</div>
							</div>
						</>
					) : (
						<>
							{/* Gray indicator when not checked in */}
							<div className="w-3 h-3 bg-gray-300 rounded-full" />
							<div>
								<div className="text-sm text-gray-500">Not checked in today</div>
								{completedTodayCount > 0 && (
									<div className="text-xs text-gray-400">
										{completedTodayCount} completed session(s)
									</div>
								)}
							</div>
						</>
					)}
				</div>

				{/* Monthly stats - OVERALL across all companies */}
				<div className="flex items-center gap-6">
					<div className="text-center">
						<div className="text-lg font-semibold text-gray-900">
							{monthlyStats.actualWorkDays}{" "}
							<span className="text-sm font-normal text-gray-400">
								/ {monthlyStats.expectedWorkDays}
							</span>
						</div>
						<div className="text-xs text-gray-500">Work Days</div>
					</div>
					<div className="text-center">
						<div className="text-lg font-semibold text-gray-900">
							{formatHours(monthlyStats.actualHours)}{" "}
							<span className="text-sm font-normal text-gray-400">
								/ {formatHours(monthlyStats.expectedHours)}
							</span>
						</div>
						<div className="text-xs text-gray-500">Total Hours</div>
					</div>
					<div className="text-center">
						<div
							className={`text-lg font-semibold ${
								monthlyStats.compTime > 0
									? "text-green-600"
									: monthlyStats.compTime < 0
										? "text-red-600"
										: "text-gray-900"
							}`}
						>
							{monthlyStats.compTime > 0 ? "+" : ""}
							{formatHours(monthlyStats.compTime)}
						</div>
						<div className="text-xs text-gray-500">Comp Time</div>
					</div>
				</div>

				{/* Check In/Out buttons - ALWAYS visible */}
				<div className="flex items-center gap-2">
					{activeEntry ? (
						<button
							type="button"
							onClick={handleCheckOut}
							disabled={isLoading}
							className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
						>
							{isLoading ? "..." : "Check Out"}
						</button>
					) : (
						<>
							{/* Company selector - show if multiple companies available */}
							{companies.length > 1 && (
								<select
									value={selectedCompanyId}
									onChange={(e) => setSelectedCompanyId(e.target.value)}
									className="text-sm border border-gray-300 rounded-md px-2 py-2"
								>
									{companies.map((company) => (
										<option key={company.id} value={company.id}>
											{company.name}
										</option>
									))}
								</select>
							)}
							<button
								type="button"
								onClick={handleCheckIn}
								disabled={isLoading}
								className="px-4 py-2 text-sm font-medium text-white rounded-md disabled:opacity-50"
								style={{ backgroundColor: isLoading ? "#9CA3AF" : "#16A34A" }}
								onMouseEnter={(e) =>
									!isLoading && (e.currentTarget.style.backgroundColor = "#15803D")
								}
								onMouseLeave={(e) =>
									!isLoading && (e.currentTarget.style.backgroundColor = "#16A34A")
								}
							>
								{isLoading ? "..." : "Check In"}
							</button>
						</>
					)}
				</div>
			</div>
		</div>
	);
}
