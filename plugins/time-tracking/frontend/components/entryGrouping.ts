// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { TimeEntry } from "../types";

/**
 * Check if two time ranges overlap.
 * Times are in HH:MM format.
 */
export function timesOverlap(
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

/**
 * Group entries by date for calendar display.
 *
 * Multi-day entries (with end_date) appear on every day in their range.
 */
export function groupEntriesByDate(entries: TimeEntry[]): Map<string, TimeEntry[]> {
	const map = new Map<string, TimeEntry[]>();
	for (const entry of entries) {
		if (entry.end_date && entry.end_date !== entry.date) {
			const endDate = new Date(entry.end_date);
			const current = new Date(entry.date);
			while (current <= endDate) {
				const dateStr = current.toISOString().split("T")[0];
				map.set(dateStr, [...(map.get(dateStr) || []), entry]);
				current.setDate(current.getDate() + 1);
			}
		} else {
			map.set(entry.date, [...(map.get(entry.date) || []), entry]);
		}
	}
	return map;
}

/** Ids of work entries whose check-in/out ranges overlap on the same date. */
export function findOverlappingEntryIds(
	entriesByDate: Map<string, TimeEntry[]>,
): Set<string> {
	const overlaps = new Set<string>();
	for (const [, dateEntries] of entriesByDate) {
		for (let i = 0; i < dateEntries.length; i++) {
			for (let j = i + 1; j < dateEntries.length; j++) {
				const e1 = dateEntries[i];
				const e2 = dateEntries[j];
				if (
					e1.entry_type === "work" &&
					e2.entry_type === "work" &&
					e1.check_in &&
					e1.check_out &&
					e2.check_in &&
					e2.check_out &&
					timesOverlap(e1.check_in, e1.check_out, e2.check_in, e2.check_out)
				) {
					overlaps.add(e1.id);
					overlaps.add(e2.id);
				}
			}
		}
	}
	return overlaps;
}
