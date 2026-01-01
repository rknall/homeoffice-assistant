// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useMemo, useState } from "react";
import { timeRecordsApi, toISODateString } from "../api";
import type { CompanyInfo, TimeRecord } from "../types";

interface TodayStatusBarProps {
	companies: CompanyInfo[]; // All companies (for check-in)
	companiesWithRecords: CompanyInfo[]; // Only companies with entries this month
	records: TimeRecord[]; // All records for the current month
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
 * TodayStatusBar - Shows today's check-in status and monthly stats
 */
export function TodayStatusBar({
	companies,
	companiesWithRecords,
	records,
	holidays,
	currentDate,
	onStatusChange,
}: TodayStatusBarProps) {
	const [todayRecords, setTodayRecords] = useState<TimeRecord[]>([]);
	const [elapsedTime, setElapsedTime] = useState<string>("");
	const [isLoading, setIsLoading] = useState(false);
	const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");

	// Initialize selectedCompanyId when companies change
	useEffect(() => {
		if (companies.length > 0 && !selectedCompanyId) {
			setSelectedCompanyId(companies[0].id);
		}
	}, [companies, selectedCompanyId]);

	// Find the active record (checked in but not checked out)
	const activeRecord = todayRecords.find(
		(r) => r.check_in && !r.check_out && r.day_type === "work",
	);

	// Calculate OVERALL monthly stats from records
	const monthlyStats = useMemo(() => {
		const year = currentDate.getFullYear();
		const month = currentDate.getMonth();

		// Expected values for the month (excluding holidays)
		const expectedWorkDays = getWorkingDaysInMonth(year, month, holidays);
		const expectedHours = expectedWorkDays * 8;

		// Count unique work days (days with work entries)
		const workDays = new Set<string>();
		let totalMinutes = 0;

		for (const record of records) {
			if (record.day_type === "work" && record.net_hours !== null) {
				workDays.add(record.date);
				totalMinutes += record.net_hours * 60;
			}
		}

		const actualWorkDays = workDays.size;
		const actualHours = totalMinutes / 60;

		// Overtime: actual hours - expected hours for days worked (not month total)
		// Only count overtime if you worked more than 8h on your actual work days
		const expectedForWorkedDays = actualWorkDays * 8;
		const overtime = Math.max(0, actualHours - expectedForWorkedDays);

		return {
			actualWorkDays,
			expectedWorkDays,
			actualHours,
			expectedHours,
			overtime,
		};
	}, [records, currentDate, holidays]);

	// Load today's records for all companies
	const loadTodayStatus = useCallback(async () => {
		if (companies.length === 0) return;

		const today = toISODateString(new Date());
		try {
			const todayData = await timeRecordsApi.list({
				start_date: today,
				end_date: today,
			});
			setTodayRecords(todayData);
		} catch (err) {
			console.error("Failed to load today status:", err);
		}
	}, [companies]);

	useEffect(() => {
		loadTodayStatus();
	}, [loadTodayStatus]);

	// Update elapsed time every minute
	useEffect(() => {
		if (!activeRecord?.check_in) {
			setElapsedTime("");
			return;
		}

		const updateElapsed = () => {
			const [hours, minutes] = activeRecord.check_in!.split(":").map(Number);
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
	}, [activeRecord]);

	// Handle check-in
	const handleCheckIn = async () => {
		const companyToUse = selectedCompanyId || companies[0]?.id;
		if (!companyToUse) return;

		setIsLoading(true);
		try {
			await timeRecordsApi.checkIn(companyToUse);
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
		if (!activeRecord) return;

		setIsLoading(true);
		try {
			await timeRecordsApi.checkOut(activeRecord.id);
			await loadTodayStatus();
			onStatusChange?.();
		} catch (err) {
			console.error("Failed to check out:", err);
		} finally {
			setIsLoading(false);
		}
	};

	// Get company name for display
	const getCompanyName = (companyId: string): string => {
		const company = companies.find((c) => c.id === companyId);
		return company?.name || "Unknown";
	};

	// Get company color
	const getCompanyColor = (companyId: string): string => {
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

	return (
		<div className="bg-white rounded-lg shadow p-4">
			<div className="flex items-center gap-6 flex-wrap">
				{/* Today's status */}
				<div className="flex items-center gap-4">
					{activeRecord ? (
						<>
							{/* Pulsing green indicator */}
							<div className="relative">
								<div className="w-3 h-3 bg-green-500 rounded-full" />
								<div className="absolute inset-0 w-3 h-3 bg-green-500 rounded-full animate-ping opacity-75" />
							</div>
							<div>
								<div className="text-sm font-medium text-gray-900">
									Checked in at{" "}
									<span className="font-semibold">{activeRecord.check_in}</span>
									{elapsedTime && (
										<span className="text-gray-500 ml-2">({elapsedTime})</span>
									)}
								</div>
								<div className="text-xs text-gray-500">
									<span
										className="inline-block px-1.5 py-0.5 rounded text-white text-xs"
										style={{
											backgroundColor: getCompanyColor(activeRecord.company_id),
										}}
									>
										{getCompanyName(activeRecord.company_id)}
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
								{todayRecords.length > 0 && (
									<div className="text-xs text-gray-400">
										{todayRecords.length} completed record(s)
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
					{activeRecord ? (
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
							{/* Company selector - only if multiple companies with records */}
							{companiesWithRecords.length > 1 && (
								<select
									value={selectedCompanyId}
									onChange={(e) => setSelectedCompanyId(e.target.value)}
									className="text-sm border border-gray-300 rounded-md px-2 py-2"
								>
									{companiesWithRecords.map((company) => (
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
								className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
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
