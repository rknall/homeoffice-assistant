// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useEffect, useState } from "react";
import type {
	CompanyInfo,
	ComplianceWarning,
	DayType,
	TimeRecord,
	TimeRecordCreate,
	TimeRecordUpdate,
} from "../types";
import { DAY_TYPE_LABELS, WARNING_LEVEL_COLORS } from "../types";

interface TimeRecordFormProps {
	record?: TimeRecord | null;
	companyId: string;
	date: string;
	onSubmit: (data: TimeRecordCreate | TimeRecordUpdate) => Promise<void>;
	onCancel: () => void;
	warnings?: ComplianceWarning[];
	isLoading?: boolean;
	/** Optional list of companies for unified view (enables company dropdown) */
	companies?: CompanyInfo[];
	/** Pre-selected company ID (from record being edited) */
	preselectedCompanyId?: string;
}

const DAY_TYPES: DayType[] = [
	"work",
	"vacation",
	"sick",
	"doctor_visit",
	"public_holiday",
	"comp_time",
	"unpaid_leave",
];

export function TimeRecordForm({
	record,
	companyId,
	date,
	onSubmit,
	onCancel,
	warnings = [],
	isLoading = false,
	companies,
	preselectedCompanyId,
}: TimeRecordFormProps) {
	// Determine initial company: use preselected, then record's company, then fallback to prop
	const initialCompanyId =
		preselectedCompanyId || record?.company_id || companyId;
	const [selectedCompanyId, setSelectedCompanyId] = useState(initialCompanyId);
	const [dayType, setDayType] = useState<DayType>(record?.day_type || "work");
	const [checkIn, setCheckIn] = useState(record?.check_in || "");
	const [checkOut, setCheckOut] = useState(record?.check_out || "");
	const [breakMinutes, setBreakMinutes] = useState<string>(
		record?.break_minutes?.toString() || "",
	);
	const [notes, setNotes] = useState(record?.notes || "");
	const [error, setError] = useState<string | null>(null);

	const isWorkType = dayType === "work" || dayType === "doctor_visit";
	const showCompanyDropdown = companies && companies.length > 0;

	useEffect(() => {
		// Reset time fields when switching to non-work types
		if (!isWorkType) {
			setCheckIn("");
			setCheckOut("");
			setBreakMinutes("");
		}
	}, [isWorkType]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		try {
			// Use selectedCompanyId for new records, or the record's existing company
			const effectiveCompanyId = record ? record.company_id : selectedCompanyId;
			const data: TimeRecordCreate | TimeRecordUpdate = {
				...(record ? {} : { company_id: effectiveCompanyId, date }),
				day_type: dayType,
				check_in: isWorkType && checkIn ? checkIn : null,
				check_out: isWorkType && checkOut ? checkOut : null,
				break_minutes: breakMinutes ? parseInt(breakMinutes, 10) : null,
				notes: notes || null,
			};
			await onSubmit(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to save record");
		}
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-4">
			{/* Date display */}
			<div className="text-sm text-gray-500">
				{new Date(date).toLocaleDateString("de-AT", {
					weekday: "long",
					year: "numeric",
					month: "long",
					day: "numeric",
				})}
			</div>

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
						disabled={!!record || isLoading}
					>
						{companies.map((company) => (
							<option key={company.id} value={company.id}>
								{company.name}
							</option>
						))}
					</select>
					{record && (
						<p className="mt-1 text-xs text-gray-500">
							Company cannot be changed for existing records
						</p>
					)}
				</div>
			)}

			{/* Day type selection */}
			<div>
				<label
					htmlFor="day-type"
					className="block text-sm font-medium text-gray-700 mb-1"
				>
					Day Type
				</label>
				<select
					id="day-type"
					value={dayType}
					onChange={(e) => setDayType(e.target.value as DayType)}
					className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					disabled={record?.is_locked || isLoading}
				>
					{DAY_TYPES.map((type) => (
						<option key={type} value={type}>
							{DAY_TYPE_LABELS[type]}
						</option>
					))}
				</select>
			</div>

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
								className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
								disabled={record?.is_locked || isLoading}
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
								className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
								disabled={record?.is_locked || isLoading}
							/>
						</div>
					</div>

					<div>
						<label
							htmlFor="break-minutes"
							className="block text-sm font-medium text-gray-700 mb-1"
						>
							Break (minutes)
						</label>
						<input
							type="number"
							id="break-minutes"
							value={breakMinutes}
							onChange={(e) => setBreakMinutes(e.target.value)}
							placeholder="Auto-calculated if empty"
							min="0"
							max="120"
							className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
							disabled={record?.is_locked || isLoading}
						/>
						<p className="mt-1 text-xs text-gray-500">
							Leave empty for automatic calculation (30 min if over 6 hours)
						</p>
					</div>
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
					disabled={record?.is_locked || isLoading}
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
					disabled={record?.is_locked || isLoading}
					className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{isLoading ? "Saving..." : record ? "Update" : "Create"}
				</button>
			</div>

			{record?.is_locked && (
				<p className="text-center text-sm text-gray-500">
					This record is locked and cannot be edited.
				</p>
			)}
		</form>
	);
}
