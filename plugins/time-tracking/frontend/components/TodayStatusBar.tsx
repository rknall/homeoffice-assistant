// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useMemo, useState } from "react";
import { errorMessage, timeEntriesApi } from "../api";
import type { CompanyInfo, TimeEntry } from "../types";
import {
	calculateBreakMinutes,
	computeMonthlyStats,
	formatHoursLabel as formatHours,
} from "./todayStats";

interface TodayStatusBarProps {
	companies: CompanyInfo[]; // All companies (for check-in)
	entries: TimeEntry[]; // All entries for the current month
	holidays: Set<string>; // Set of holiday date strings (YYYY-MM-DD)
	currentDate: Date;
	onStatusChange?: () => void;
	onError?: (message: string) => void;
}

/**
 * TodayStatusBar - Shows today's check-in status and monthly stats
 */
export function TodayStatusBar({
	companies,
	entries,
	holidays,
	currentDate,
	onStatusChange,
	onError,
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

	// Overall monthly stats across all companies
	const monthlyStats = useMemo(
		() => computeMonthlyStats(entries, currentDate, holidays),
		[entries, currentDate, holidays],
	);

	// Load today's entries
	const loadTodayStatus = useCallback(async () => {
		if (companies.length === 0) return;

		try {
			const todayData = await timeEntriesApi.getToday();
			setTodayEntries(todayData);
		} catch (err) {
			onError?.(errorMessage(err, "Failed to load today status"));
		}
	}, [companies, onError]);

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
			onError?.(errorMessage(err, "Failed to check in"));
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
			onError?.(errorMessage(err, "Failed to check out"));
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

	// Calculate today's total worked hours (completed sessions only)
	const todayWorkedHours = useMemo(() => {
		let totalMinutes = 0;
		const dailyGross = todayEntries
			.filter((e) => !e.is_open && e.entry_type === "work" && e.gross_hours !== null)
			.reduce((sum, e) => sum + (e.gross_hours || 0), 0);

		// Calculate break for today based on total gross hours
		const breakMinutes = calculateBreakMinutes(dailyGross);
		totalMinutes = dailyGross * 60 - breakMinutes;

		return totalMinutes / 60;
	}, [todayEntries]);

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
								{todayWorkedHours > 0 ? (
									<>
										<div className="text-sm font-medium text-gray-700">
											{formatHours(todayWorkedHours)} worked today
										</div>
										<div className="text-xs text-gray-400">
											No session running
										</div>
									</>
								) : (
									<div className="text-sm text-gray-500">No sessions today</div>
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
