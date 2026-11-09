// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

interface LeaveFieldsProps {
	selectedDate: string;
	endDate: string;
	onEndDateChange: (value: string) => void;
	supportsHalfDay: boolean;
	isHalfDay: boolean;
	onHalfDayChange: (value: boolean) => void;
	disabled: boolean;
}

/** End date and half-day inputs for vacation and sick entries. */
export function LeaveFields({
	selectedDate,
	endDate,
	onEndDateChange,
	supportsHalfDay,
	isHalfDay,
	onHalfDayChange,
	disabled,
}: LeaveFieldsProps) {
	return (
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
					onChange={(e) => onEndDateChange(e.target.value)}
					className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					disabled={disabled}
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
						onChange={(e) => onHalfDayChange(e.target.checked)}
						className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						disabled={disabled}
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
	);
}
