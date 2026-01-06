// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useMemo, useState } from "react";
import type { CompanyInfo, TimeEntry } from "../types";
import { ENTRY_TYPE_LABELS, WORK_LOCATION_LABELS } from "../types";

interface TableViewProps {
	entries: TimeEntry[];
	overlappingEntryIds: Set<string>;
	companies: CompanyInfo[];
	getCompanyColor: (companyId: string | null) => string;
	onEntryClick: (entry: TimeEntry) => void;
	onDeleteEntry?: (entry: TimeEntry) => void;
	isLoading: boolean;
}

interface TableRow {
	id: string;
	entry: TimeEntry;
	isFirstOfDay: boolean;
}

/**
 * TableView - Tabular list of time entries
 *
 * Displays entries in a sortable table format with company colors
 * and overlap highlighting.
 */
export function TableView({
	entries,
	overlappingEntryIds,
	companies,
	getCompanyColor,
	onEntryClick,
	onDeleteEntry,
	isLoading,
}: TableViewProps) {
	const [sortField, setSortField] = useState<"date" | "company">("date");
	const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

	// Create company lookup map
	const companyNameMap = useMemo(() => {
		const map = new Map<string, string>();
		for (const company of companies) {
			map.set(company.id, company.name);
		}
		return map;
	}, [companies]);

	// Get company name by ID
	const getCompanyName = (companyId: string | null): string => {
		if (!companyId) return "No Company";
		return companyNameMap.get(companyId) || "Unknown";
	};

	// Sort and flatten entries into table rows
	const tableRows = useMemo((): TableRow[] => {
		// Sort entries
		const sorted = [...entries].sort((a, b) => {
			let comparison = 0;
			if (sortField === "date") {
				// Sort by date first, then by check_in time
				comparison = a.date.localeCompare(b.date);
				if (comparison === 0 && a.check_in && b.check_in) {
					comparison = a.check_in.localeCompare(b.check_in);
				}
			} else if (sortField === "company") {
				comparison = getCompanyName(a.company_id).localeCompare(
					getCompanyName(b.company_id),
				);
			}
			return sortDirection === "asc" ? comparison : -comparison;
		});

		// Group by date to mark first of day
		const rows: TableRow[] = [];
		let lastDate = "";

		for (const entry of sorted) {
			const isFirstOfDay = entry.date !== lastDate;
			lastDate = entry.date;

			rows.push({
				id: entry.id,
				entry,
				isFirstOfDay,
			});
		}

		return rows;
	}, [entries, sortField, sortDirection, companyNameMap]);

	// Toggle sort
	const handleSort = (field: "date" | "company") => {
		if (sortField === field) {
			setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
		} else {
			setSortField(field);
			setSortDirection("asc");
		}
	};

	// Format date for display
	const formatDate = (dateStr: string): string => {
		const date = new Date(dateStr);
		return date.toLocaleDateString("de-AT", {
			day: "2-digit",
			month: "2-digit",
			year: "numeric",
		});
	};

	// Format time for display (only HH:MM, no seconds)
	const formatTime = (time: string | null): string => {
		if (!time) return "--:--";
		// Remove seconds if present (e.g., "09:15:00" -> "09:15")
		const parts = time.split(":");
		return `${parts[0]}:${parts[1]}`;
	};

	// Calculate duration in hours
	const calculateDuration = (
		checkIn: string | null,
		checkOut: string | null,
	): string => {
		if (!checkIn || !checkOut) return "-";

		const [inH, inM] = checkIn.split(":").map(Number);
		const [outH, outM] = checkOut.split(":").map(Number);

		let minutes = outH * 60 + outM - (inH * 60 + inM);
		// Handle overnight
		if (minutes < 0) minutes += 24 * 60;

		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		return `${hours}:${mins.toString().padStart(2, "0")}`;
	};

	// Check if entry is editable
	const isEditable = (entry: TimeEntry): boolean => {
		return entry.entry_type !== "public_holiday" && !entry.is_locked;
	};

	// Sort indicator
	const SortIndicator = ({ field }: { field: "date" | "company" }) => {
		if (sortField !== field) return null;
		return <span className="ml-1">{sortDirection === "asc" ? "↑" : "↓"}</span>;
	};

	return (
		<div className="bg-white rounded-lg shadow overflow-hidden">
			<div className="overflow-x-auto">
				<table className="w-full">
					<thead className="bg-gray-50">
						<tr>
							<th
								className="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort("date")}
							>
								Date
								<SortIndicator field="date" />
							</th>
							<th
								className="px-4 py-3 text-left text-sm font-medium text-gray-500 cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort("company")}
							>
								Company
								<SortIndicator field="company" />
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Type
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Check In
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Check Out
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Duration
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Location
							</th>
							<th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
								Actions
							</th>
						</tr>
					</thead>
					<tbody>
						{tableRows.length === 0 ? (
							<tr>
								<td colSpan={8} className="px-4 py-8 text-center text-gray-500">
									{isLoading ? "Loading..." : "No entries this month"}
								</td>
							</tr>
						) : (
							tableRows.map((row, index) => {
								const hasOverlap = overlappingEntryIds.has(row.entry.id);
								const editable = isEditable(row.entry);
								const companyColor = getCompanyColor(row.entry.company_id);

								return (
									<tr
										key={row.id}
										className={`
                      ${row.isFirstOfDay ? "border-t border-gray-200" : ""}
                      ${row.entry.is_locked ? "opacity-60" : ""}
                      ${hasOverlap ? "bg-red-50" : index % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      ${editable ? "cursor-pointer hover:bg-blue-50" : ""}
                      transition-colors
                    `}
									>
										{/* Date */}
										<td className="px-4 py-2 text-sm text-gray-900">
											{row.isFirstOfDay ? formatDate(row.entry.date) : ""}
										</td>

										{/* Company */}
										<td className="px-4 py-2">
											<span
												className="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
												style={{ backgroundColor: companyColor }}
											>
												{getCompanyName(row.entry.company_id)}
											</span>
										</td>

										{/* Entry type */}
										<td className="px-4 py-2">
											<span
												className="inline-block px-2 py-0.5 rounded text-xs font-medium"
												style={{
													backgroundColor: `${companyColor}20`,
													color: companyColor,
												}}
											>
												{ENTRY_TYPE_LABELS[row.entry.entry_type] ||
													row.entry.entry_type}
												{row.entry.is_half_day && " (½)"}
											</span>
											{row.entry.is_open && (
												<span className="ml-1 text-xs text-green-600">(open)</span>
											)}
											{row.entry.end_date && row.entry.end_date !== row.entry.date && (
												<span className="ml-1 text-xs text-gray-500">
													→ {formatDate(row.entry.end_date)}
												</span>
											)}
										</td>

										{/* Check In */}
										<td className="px-4 py-2 text-sm text-gray-900 font-mono">
											{formatTime(row.entry.check_in)}
										</td>

										{/* Check Out */}
										<td className="px-4 py-2 text-sm text-gray-900 font-mono">
											{formatTime(row.entry.check_out)}
										</td>

										{/* Duration */}
										<td className="px-4 py-2 text-sm text-gray-900 font-mono">
											{calculateDuration(
												row.entry.check_in,
												row.entry.check_out,
											)}
										</td>

										{/* Location */}
										<td className="px-4 py-2 text-sm text-gray-500">
											{row.entry.work_location
												? WORK_LOCATION_LABELS[row.entry.work_location]
												: "-"}
										</td>

										{/* Actions */}
										<td className="px-4 py-2">
											<div className="flex items-center gap-1">
												{editable && (
													<>
														<button
															type="button"
															onClick={(e) => {
																e.stopPropagation();
																onEntryClick(row.entry);
															}}
															className={`
                              px-2 py-1 text-xs font-medium rounded
                              ${hasOverlap ? "bg-red-600 text-white hover:bg-red-700" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}
                            `}
														>
															{hasOverlap ? "Fix" : "Edit"}
														</button>
														{onDeleteEntry && (
															<button
																type="button"
																onClick={(e) => {
																	e.stopPropagation();
																	onDeleteEntry(row.entry);
																}}
																className="px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-700 hover:bg-red-200"
															>
																Delete
															</button>
														)}
													</>
												)}
												{row.entry.is_locked && (
													<span className="text-xs text-gray-400">Locked</span>
												)}
											</div>
										</td>
									</tr>
								);
							})
						)}
					</tbody>
				</table>
			</div>

			{/* Legend */}
			<div className="p-3 border-t border-gray-200 flex items-center gap-4 text-xs text-gray-500">
				<div className="flex items-center gap-1">
					<div className="w-3 h-3 rounded bg-red-50 border border-red-200" />
					<span>Overlapping entries</span>
				</div>
				<div className="flex items-center gap-1">
					<span>Click row to view details</span>
				</div>
			</div>
		</div>
	);
}
