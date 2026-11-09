// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { toISODateString } from "../api";
import type { TimeEntry } from "../types";

export interface MonthlyStats {
	actualWorkDays: number;
	expectedWorkDays: number;
	expectedWorkDaysSoFar: number;
	actualHours: number;
	expectedHours: number;
	expectedHoursSoFar: number;
	compTime: number;
}

/**
 * Calculate the number of base working days (Mon-Fri, excluding holidays) in a given month
 */
export function getBaseWorkingDaysInMonth(
	year: number,
	month: number,
	holidays: Set<string>,
): number {
	const firstDay = new Date(year, month, 1);
	const lastDay = new Date(year, month + 1, 0);
	let workingDays = 0;

	const current = new Date(firstDay);
	while (current <= lastDay) {
		const dayOfWeek = current.getDay();
		const dateStr = toISODateString(current);
		// Count as working day if it's a weekday AND not a holiday
		if (dayOfWeek !== 0 && dayOfWeek !== 6 && !holidays.has(dateStr)) {
			workingDays++;
		}
		current.setDate(current.getDate() + 1);
	}

	return workingDays;
}

/**
 * Count effective leave days applying priority rules:
 * 1. National Holiday > 2. Weekend > 3. Sickness > 4. Vacation
 */
export function countEffectiveLeaveDays(
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
		const current = new Date(startDate);
		while (current <= endDate) {
			// Only count days within the target month
			if (current >= monthStart && current <= monthEnd) {
				const dateStr = toISODateString(current);
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
			current.setDate(current.getDate() + 1);
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
export function calculateBreakMinutes(grossHours: number): number {
	if (grossHours > 6) return 30;
	return 0;
}

/**
 * Compute the overall monthly stats (work days, hours, comp time) from entries.
 */
export function computeMonthlyStats(
	entries: TimeEntry[],
	currentDate: Date,
	holidays: Set<string>,
): MonthlyStats {
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
			// Format as YYYY-MM-DD for consistent comparison
			const dateStr = `${currentDay.getFullYear()}-${String(currentDay.getMonth() + 1).padStart(2, "0")}-${String(currentDay.getDate()).padStart(2, "0")}`;
			const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
			const isHoliday = holidays.has(dateStr);

			// Check if this day has leave (vacation or sick) using string comparison
			const hasLeave = entries.some(e => {
				if (e.entry_type !== "vacation" && e.entry_type !== "sick") return false;
				const startDate = e.date;
				const endDate = e.end_date || e.date;
				return dateStr >= startDate && dateStr <= endDate;
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
}

/** Format hours for display (handles negative values). */
export function formatHoursLabel(hours: number): string {
	const absHours = Math.abs(hours);
	const h = Math.floor(absHours);
	const m = Math.round((absHours - h) * 60);
	const sign = hours < 0 ? "-" : "";
	if (m === 0) return `${sign}${h}h`;
	return `${sign}${h}h ${m}m`;
}
