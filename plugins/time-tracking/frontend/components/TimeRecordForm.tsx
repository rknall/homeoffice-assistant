// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from "react";
import type {
	CompanyInfo,
	ComplianceWarning,
	EntryType,
	TimeEntry,
	TimeEntryCreate,
	TimeEntryUpdate,
	WorkLocation,
} from "../types";
import {
	ENTRY_TYPE_LABELS,
	WARNING_LEVEL_COLORS,
	WORK_LOCATION_LABELS,
} from "../types";

interface TimeEntryFormProps {
	entry?: TimeEntry | null;
	companyId: string;
	date: string;
	onSubmit: (data: TimeEntryCreate | TimeEntryUpdate) => Promise<void>;
	onCancel: () => void;
	warnings?: ComplianceWarning[];
	isLoading?: boolean;
	/** Optional list of companies for unified view (enables company dropdown) */
	companies?: CompanyInfo[];
	/** Pre-selected company ID (from entry being edited) */
	preselectedCompanyId?: string;
}

const ENTRY_TYPES: EntryType[] = [
	"work",
	"vacation",
	"sick",
	"doctor_visit",
	"public_holiday",
	"comp_time",
	"unpaid_leave",
	"parental_leave",
	"training",
	"other",
];

const WORK_LOCATIONS: WorkLocation[] = ["office", "remote", "client_site", "travel"];

export function TimeRecordForm({
	entry,
	companyId,
	date,
	onSubmit,
	onCancel,
	warnings = [],
	isLoading = false,
	companies,
	preselectedCompanyId,
}: TimeEntryFormProps) {
	// Determine initial company: use preselected, then entry's company, then fallback to prop
	const initialCompanyId =
		preselectedCompanyId || entry?.company_id || companyId;
	const [selectedCompanyId, setSelectedCompanyId] = useState(initialCompanyId);
	const [selectedDate, setSelectedDate] = useState(date);
	const [entryType, setEntryType] = useState<EntryType>(
		entry?.entry_type || "work",
	);
	const [checkIn, setCheckIn] = useState(entry?.check_in || "");
	const [checkOut, setCheckOut] = useState(entry?.check_out || "");
	const [workLocation, setWorkLocation] = useState<WorkLocation | "">(
		entry?.work_location || "",
	);
	const [notes, setNotes] = useState(entry?.notes || "");
	const [endDate, setEndDate] = useState(entry?.end_date || "");
	const [isHalfDay, setIsHalfDay] = useState(entry?.is_half_day || false);
	const [error, setError] = useState<string | null>(null);
	const [timeError, setTimeError] = useState<string | null>(null);

	const isWorkType = entryType === "work" || entryType === "doctor_visit";
	const isLeaveType = entryType === "vacation" || entryType === "sick";
	const supportsHalfDay = entryType === "vacation";
	const showCompanyDropdown = companies && companies.length > 0;
	const isNewEntry = !entry;

	// Validate times: check-out must be after check-in
	const validateTimes = (inTime: string, outTime: string): boolean => {
		if (!inTime || !outTime) return true; // No validation if times are incomplete
		const [inH, inM] = inTime.split(":").map(Number);
		const [outH, outM] = outTime.split(":").map(Number);
		const inMinutes = inH * 60 + inM;
		const outMinutes = outH * 60 + outM;
		return outMinutes > inMinutes;
	};

	// Update time error when times change
	useEffect(() => {
		if (isWorkType && checkIn && checkOut) {
			if (!validateTimes(checkIn, checkOut)) {
				setTimeError("Check-out time must be after check-in time");
			} else {
				setTimeError(null);
			}
		} else {
			setTimeError(null);
		}
	}, [checkIn, checkOut, isWorkType]);

	useEffect(() => {
		// Reset time fields when switching to non-work types
		if (!isWorkType) {
			setCheckIn("");
			setCheckOut("");
			setWorkLocation("");
		}
		// Reset leave-specific fields when switching to non-leave types
		if (!isLeaveType) {
			setEndDate("");
			setIsHalfDay(false);
		}
		// Reset half-day when switching away from vacation
		if (!supportsHalfDay) {
			setIsHalfDay(false);
		}
	}, [isWorkType, isLeaveType, supportsHalfDay]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		// Prevent submission if there's a time validation error
		if (timeError) {
			return;
		}

		try {
			// Use selectedCompanyId for new entries, or the entry's existing company
			const effectiveCompanyId = entry ? entry.company_id : selectedCompanyId;
			const data: TimeEntryCreate | TimeEntryUpdate = {
				...(entry
					? {}
					: { company_id: effectiveCompanyId, date: selectedDate }),
				entry_type: entryType,
				check_in: isWorkType && checkIn ? checkIn : null,
				check_out: isWorkType && checkOut ? checkOut : null,
				work_location: isWorkType && workLocation ? workLocation : null,
				notes: notes || null,
				// Leave-specific fields
				end_date: isLeaveType && endDate ? endDate : null,
				is_half_day: supportsHalfDay ? isHalfDay : false,
			};
			await onSubmit(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to save entry");
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-4">
			{/* Date selection (editable for new entries) */}
			{isNewEntry ? (
				<div>
					<label
						htmlFor="entry-date"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Date
					</label>
					<input
						type="date"
						id="entry-date"
						value={selectedDate}
						onChange={(e) => setSelectedDate(e.target.value)}
						className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
						disabled={isLoading}
					/>
				</div>
			) : (
				<div className="text-sm text-gray-500">
					{new Date(date).toLocaleDateString("de-AT", {
						weekday: "long",
						year: "numeric",
						month: "long",
						day: "numeric",
					})}
				</div>
			)}

			{/* Company selection (only for unified view with multiple companies) */}
			{showCompanyDropdown && (
				<div>
					<label
						htmlFor="company"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Company
					</label>
					<select
						id="company"
						value={selectedCompanyId}
						onChange={(e) => setSelectedCompanyId(e.target.value)}
						className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
						disabled={!!entry || isLoading}
					>
						{companies.map((company) => (
							<option key={company.id} value={company.id}>
								{company.name}
							</option>
						))}
					</select>
					{entry && (
						<p className="mt-1 text-xs text-gray-500">
							Company cannot be changed for existing entries
						</p>
					)}
				</div>
			)}

			{/* Entry type selection */}
			<div>
				<label
					htmlFor="entry-type"
					className="block text-sm font-medium text-gray-700 mb-1"
				>
					Entry Type
				</label>
				<select
					id="entry-type"
					value={entryType}
					onChange={(e) => setEntryType(e.target.value as EntryType)}
					className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					disabled={entry?.is_locked || isLoading}
				>
					{ENTRY_TYPES.map((type) => (
						<option key={type} value={type}>
							{ENTRY_TYPE_LABELS[type]}
						</option>
					))}
				</select>
			</div>

			{/* Leave-specific fields (vacation, sick) */}
			{isLeaveType && (
				<>
					{/* End date for multi-day leave */}
					<div>
						<label
							htmlFor="end-date"
							className="block text-sm font-medium text-gray-700 mb-1"
						>
							End Date (for multi-day leave)
						</label>
						<input
							type="date"
							id="end-date"
							value={endDate}
							min={selectedDate}
							onChange={(e) => setEndDate(e.target.value)}
							className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
							disabled={entry?.is_locked || isLoading}
						/>
						<p className="mt-1 text-xs text-gray-500">
							Leave empty for single-day entries
						</p>
					</div>

					{/* Half-day checkbox (vacation only) */}
					{supportsHalfDay && (
						<div className="flex items-center gap-2">
							<input
								type="checkbox"
								id="is-half-day"
								checked={isHalfDay}
								onChange={(e) => setIsHalfDay(e.target.checked)}
								className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								disabled={entry?.is_locked || isLoading}
							/>
							<label
								htmlFor="is-half-day"
								className="text-sm font-medium text-gray-700"
							>
								Half-day vacation (4 hours)
							</label>
						</div>
					)}

					{/* Warning about half-day overtime */}
					{supportsHalfDay && isHalfDay && (
						<p className="text-xs text-amber-600">
							Note: Overtime is not permitted on half-vacation days
						</p>
					)}
				</>
			)}

			{/* Time fields (only for work/doctor_visit) */}
			{isWorkType && (
				<>
					<div className="grid grid-cols-2 gap-4">
						<div>
							<label
								htmlFor="check-in"
								className="block text-sm font-medium text-gray-700 mb-1"
							>
								Check In
							</label>
							<input
								type="time"
								id="check-in"
								value={checkIn}
								onChange={(e) => setCheckIn(e.target.value)}
								className={`w-full rounded-md shadow-sm focus:ring-blue-500 ${
									timeError
										? "border-red-500 focus:border-red-500"
										: "border-gray-300 focus:border-blue-500"
								}`}
								disabled={entry?.is_locked || isLoading}
							/>
						</div>
						<div>
							<label
								htmlFor="check-out"
								className="block text-sm font-medium text-gray-700 mb-1"
							>
								Check Out
							</label>
							<input
								type="time"
								id="check-out"
								value={checkOut}
								onChange={(e) => setCheckOut(e.target.value)}
								className={`w-full rounded-md shadow-sm focus:ring-blue-500 ${
									timeError
										? "border-red-500 focus:border-red-500"
										: "border-gray-300 focus:border-blue-500"
								}`}
								disabled={entry?.is_locked || isLoading}
							/>
						</div>
					</div>
					{/* Time validation error */}
					{timeError && <p className="text-sm text-red-600">{timeError}</p>}

					{/* Work location */}
					<div>
						<label
							htmlFor="work-location"
							className="block text-sm font-medium text-gray-700 mb-1"
						>
							Work Location
						</label>
						<select
							id="work-location"
							value={workLocation}
							onChange={(e) =>
								setWorkLocation(e.target.value as WorkLocation | "")
							}
							className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
							disabled={entry?.is_locked || isLoading}
						>
							<option value="">Not specified</option>
							{WORK_LOCATIONS.map((loc) => (
								<option key={loc} value={loc}>
									{WORK_LOCATION_LABELS[loc]}
								</option>
							))}
						</select>
					</div>

					<p className="text-xs text-gray-500">
						Break time is automatically calculated (30 min if over 6 hours)
					</p>
				</>
			)}

			{/* Notes */}
			<div>
				<label
					htmlFor="notes"
					className="block text-sm font-medium text-gray-700 mb-1"
				>
					Notes
				</label>
				<textarea
					id="notes"
					value={notes}
					onChange={(e) => setNotes(e.target.value)}
					rows={2}
					className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					disabled={entry?.is_locked || isLoading}
					placeholder="Optional notes..."
				/>
			</div>

			{/* Compliance warnings */}
			{warnings.length > 0 && (
				<div className="space-y-2">
					{warnings.map((warning, index) => {
						const colors = WARNING_LEVEL_COLORS[warning.level];
						return (
							<div
								key={index}
								className={`p-3 rounded-md border ${colors.bg} ${colors.border}`}
							>
								<p className={`text-sm font-medium ${colors.text}`}>
									{warning.message}
								</p>
								{warning.law_reference && (
									<p className={`text-xs mt-1 ${colors.text} opacity-75`}>
										Reference: {warning.law_reference}
									</p>
								)}
							</div>
						);
					})}
				</div>
			)}

			{/* Error message */}
			{error && (
				<div className="p-3 rounded-md bg-red-50 border border-red-200">
					<p className="text-sm text-red-700">{error}</p>
				</div>
			)}

			{/* Actions */}
			<div className="flex justify-end gap-3 pt-4">
				<button
					type="button"
					onClick={onCancel}
					disabled={isLoading}
					className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
				>
					Cancel
				</button>
				<button
					type="submit"
					disabled={entry?.is_locked || isLoading || !!timeError}
					className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{isLoading ? "Saving..." : entry ? "Update" : "Create"}
				</button>
			</div>

			{entry?.is_locked && (
				<p className="text-center text-sm text-gray-500">
					This entry is locked and cannot be edited.
				</p>
			)}
		</form>
	);
}

// Legacy alias for backward compatibility
export { TimeRecordForm as TimeEntryForm };
