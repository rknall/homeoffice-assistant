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
 * Calculate the number of working days (Mon-Fri, excluding holidays) in a given month
 */
function getWorkingDaysInMonth(
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

		// Expected values for the month (excluding holidays)
		const expectedWorkDays = getWorkingDaysInMonth(year, month, holidays);
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

		// Overtime: actual hours - expected hours for days worked (not month total)
		const expectedForWorkedDays = actualWorkDays * 8;
		const overtime = Math.max(0, actualNetHours - expectedForWorkedDays);

		return {
			actualWorkDays,
			expectedWorkDays,
			actualHours: actualNetHours,
			expectedHours,
			overtime,
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

	// Format hours for display
	const formatHours = (hours: number): string => {
		const h = Math.floor(hours);
		const m = Math.round((hours - h) * 60);
		if (m === 0) return `${h}h`;
		return `${h}h ${m}m`;
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
								monthlyStats.overtime > 0 ? "text-green-600" : "text-gray-900"
							}`}
						>
							{monthlyStats.overtime > 0 ? "+" : ""}
							{formatHours(monthlyStats.overtime)}
						</div>
						<div className="text-xs text-gray-500">Overtime</div>
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
