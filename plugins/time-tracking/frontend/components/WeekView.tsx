// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useMemo } from "react";
import { formatHours, formatTime, getWeekStart, toISODateString } from "../api";
import type { ComplianceWarning, TimeEntry } from "../types";
import { ENTRY_TYPE_LABELS } from "../types";

interface WeekViewProps {
	entries: TimeEntry[];
	currentDate: Date;
	onDateChange: (date: Date) => void;
	onDayClick: (date: string, entries?: TimeEntry[]) => void;
	warnings?: Record<string, ComplianceWarning[]>;
	holidays?: Record<string, string>;
	isLoading?: boolean;
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function WeekView({
	entries,
	currentDate,
	onDateChange,
	onDayClick,
	warnings = {},
	holidays = {},
	isLoading = false,
}: WeekViewProps) {
	const weekStart = useMemo(() => getWeekStart(currentDate), [currentDate]);

	const weekDays = useMemo(() => {
		const days = [];
		for (let i = 0; i < 7; i++) {
			const date = new Date(weekStart);
			date.setDate(date.getDate() + i);
			days.push(date);
		}
		return days;
	}, [weekStart]);

	// Group entries by date (can have multiple entries per day)
	const entriesByDate = useMemo(() => {
		const map: Record<string, TimeEntry[]> = {};
		for (const entry of entries) {
			if (!map[entry.date]) {
				map[entry.date] = [];
			}
			map[entry.date].push(entry);
		}
		return map;
	}, [entries]);

	// Calculate total hours (gross - break estimate)
	const totalHours = useMemo(() => {
		let total = 0;
		for (const entry of entries) {
			if (entry.gross_hours !== null) {
				// Subtract 30 min break for work sessions over 6 hours
				const breakHours = entry.gross_hours > 6 ? 0.5 : 0;
				total += entry.gross_hours - breakHours;
			}
		}
		return total;
	}, [entries]);

	const goToPrevWeek = () => {
		const prev = new Date(weekStart);
		prev.setDate(prev.getDate() - 7);
		onDateChange(prev);
	};

	const goToNextWeek = () => {
		const next = new Date(weekStart);
		next.setDate(next.getDate() + 7);
		onDateChange(next);
	};

	const goToToday = () => {
		onDateChange(new Date());
	};

	const formatWeekRange = () => {
		const end = new Date(weekStart);
		end.setDate(end.getDate() + 6);

		const startStr = weekStart.toLocaleDateString("de-AT", {
			day: "2-digit",
			month: "2-digit",
		});
		const endStr = end.toLocaleDateString("de-AT", {
			day: "2-digit",
			month: "2-digit",
			year: "numeric",
		});
		return `${startStr} - ${endStr}`;
	};

	const isToday = (date: Date) => {
		const today = new Date();
		return (
			date.getDate() === today.getDate() &&
			date.getMonth() === today.getMonth() &&
			date.getFullYear() === today.getFullYear()
		);
	};

	return (
		<div className="bg-white rounded-lg shadow">
			{/* Header with navigation */}
			<div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
				<div className="flex items-center gap-2">
					<button
						type="button"
						onClick={goToPrevWeek}
						className="p-2 rounded-md hover:bg-gray-100"
						aria-label="Previous week"
					>
						<svg
							className="w-5 h-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<title>Previous week</title>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={2}
								d="M15 19l-7-7 7-7"
							/>
						</svg>
					</button>
					<span className="text-lg font-semibold text-gray-900 min-w-[200px] text-center">
						{formatWeekRange()}
					</span>
					<button
						type="button"
						onClick={goToNextWeek}
						className="p-2 rounded-md hover:bg-gray-100"
						aria-label="Next week"
					>
						<svg
							className="w-5 h-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<title>Next week</title>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								strokeWidth={2}
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</button>
				</div>
				<div className="flex items-center gap-4">
					<button
						type="button"
						onClick={goToToday}
						className="px-3 py-1 text-sm font-medium text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200"
					>
						Today
					</button>
					<div className="text-sm text-gray-500">
						Total:{" "}
						<span className="font-semibold text-gray-900">
							{formatHours(totalHours)}
						</span>
					</div>
				</div>
			</div>

			{/* Week grid */}
			{isLoading ? (
				<div className="p-8 text-center text-gray-500">Loading...</div>
			) : (
				<div className="grid grid-cols-7 divide-x divide-gray-200">
					{weekDays.map((date, index) => {
						const dateStr = toISODateString(date);
						const dayEntries = entriesByDate[dateStr] || [];
						const dayWarnings = warnings[dateStr] || [];
						const holidayName = holidays[dateStr];
						const isWeekend = date.getDay() === 0 || date.getDay() === 6;
						const today = isToday(date);

						// Calculate total hours for the day
						let dayTotalHours = 0;
						for (const entry of dayEntries) {
							if (entry.gross_hours !== null) {
								const breakHours = entry.gross_hours > 6 ? 0.5 : 0;
								dayTotalHours += entry.gross_hours - breakHours;
							}
						}

						return (
							<button
								type="button"
								key={dateStr}
								onClick={() => onDayClick(dateStr, dayEntries)}
								className={`p-3 text-left hover:bg-gray-50 transition-colors min-h-[120px] flex flex-col ${
									today ? "bg-blue-50" : isWeekend ? "bg-gray-50" : ""
								}`}
							>
								{/* Day header */}
								<div className="flex items-center justify-between mb-2">
									<span
										className={`text-xs font-medium ${today ? "text-blue-600" : "text-gray-500"}`}
									>
										{WEEKDAYS[index]}
									</span>
									<span
										className={`text-sm font-semibold ${
											today
												? "text-white bg-blue-600 w-7 h-7 rounded-full flex items-center justify-center"
												: "text-gray-900"
										}`}
									>
										{date.getDate()}
									</span>
								</div>

								{/* Holiday indicator */}
								{holidayName && (
									<div className="text-xs text-purple-600 font-medium mb-1 truncate">
										{holidayName}
									</div>
								)}

								{/* Entries content */}
								{dayEntries.length > 0 ? (
									<div className="flex-1 space-y-1">
										{dayEntries.map((entry) => (
											<div key={entry.id} className="text-xs">
												{/* Entry type badge */}
												<span
													className="inline-block px-2 py-0.5 font-medium rounded-full bg-blue-100 text-blue-800"
												>
													{ENTRY_TYPE_LABELS[entry.entry_type]}
												</span>

												{/* Time info for work entries */}
												{(entry.entry_type === "work" ||
													entry.entry_type === "doctor_visit") &&
													entry.check_in && (
													<div className="text-gray-600 mt-0.5">
														{formatTime(entry.check_in)} -{" "}
														{entry.check_out
															? formatTime(entry.check_out)
															: "..."}
														{entry.is_open && (
															<span className="text-green-600 ml-1">(open)</span>
														)}
													</div>
												)}

												{/* Lock indicator */}
												{entry.is_locked && (
													<svg
														className="w-3 h-3 text-gray-400 inline-block ml-1"
														fill="currentColor"
														viewBox="0 0 20 20"
													>
														<title>Locked</title>
														<path
															fillRule="evenodd"
															d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
															clipRule="evenodd"
														/>
													</svg>
												)}
											</div>
										))}

										{/* Total hours for day */}
										{dayTotalHours > 0 && (
											<div className="text-sm font-medium text-gray-900 mt-1">
												{formatHours(dayTotalHours)}
											</div>
										)}
									</div>
								) : (
									<div className="flex-1 flex items-center justify-center">
										<span className="text-xs text-gray-400">No entry</span>
									</div>
								)}

								{/* Warning indicators */}
								{dayWarnings.length > 0 && (
									<div className="mt-2 flex gap-1">
										{dayWarnings.map((warning, i) => (
											<span
												key={i}
												className={`w-2 h-2 rounded-full ${
													warning.level === "error"
														? "bg-red-500"
														: warning.level === "warning"
															? "bg-yellow-500"
															: "bg-blue-500"
												}`}
												title={warning.message}
											/>
										))}
									</div>
								)}
							</button>
						);
					})}
				</div>
			)}
		</div>
	);
}
