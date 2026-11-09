// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { CompanyInfo } from "../types";

export type ViewMode = "calendar" | "table";

interface PageControlsProps {
	companiesWithEntries: CompanyInfo[];
	visibleCompanyIds: Set<string>;
	onToggleCompany: (companyId: string) => void;
	monthYearDisplay: string;
	onPreviousMonth: () => void;
	onNextMonth: () => void;
	onToday: () => void;
	viewMode: ViewMode;
	onViewModeChange: (mode: ViewMode) => void;
	onAddEntry: () => void;
}

/** Company filters, month navigation, view toggle and the Add Entry button. */
export function PageControls({
	companiesWithEntries,
	visibleCompanyIds,
	onToggleCompany,
	monthYearDisplay,
	onPreviousMonth,
	onNextMonth,
	onToday,
	viewMode,
	onViewModeChange,
	onAddEntry,
}: PageControlsProps) {
	return (
	<div className="flex items-center justify-between flex-wrap gap-4">
		{/* Company filter toggles - only show companies with entries this month */}
		<div className="flex flex-wrap gap-2">
			{companiesWithEntries.map((company) => {
				const isVisible = visibleCompanyIds.has(company.id);
				return (
					<button
						key={company.id}
						type="button"
						onClick={() => onToggleCompany(company.id)}
						className={`
							px-3 py-1.5 text-sm font-medium rounded-full border-2 transition-colors
							${
								isVisible
									? "text-white border-transparent"
									: "bg-white text-gray-500 border-gray-300 hover:border-gray-400"
							}
						`}
						style={
							isVisible
								? {
										backgroundColor: company.color,
										borderColor: company.color,
									}
								: undefined
						}
					>
						{company.name}
					</button>
				);
			})}
		</div>

		{/* Month navigation and view toggle */}
		<div className="flex items-center gap-2">
			<button
				type="button"
				onClick={onPreviousMonth}
				className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
				aria-label="Previous month"
			>
				<svg
					className="w-5 h-5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					aria-hidden="true"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M15 19l-7-7 7-7"
					/>
				</svg>
			</button>

			<button
				type="button"
				onClick={onToday}
				className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
			>
				Today
			</button>

			<span className="min-w-[140px] text-center text-lg font-semibold text-gray-900">
				{monthYearDisplay}
			</span>

			<button
				type="button"
				onClick={onNextMonth}
				className="p-2 text-gray-600 hover:bg-gray-100 rounded-md"
				aria-label="Next month"
			>
				<svg
					className="w-5 h-5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					aria-hidden="true"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M9 5l7 7-7 7"
					/>
				</svg>
			</button>

			{/* View toggle */}
			<div className="ml-2 flex rounded-md overflow-hidden border border-gray-300">
				<button
					type="button"
					onClick={() => onViewModeChange("calendar")}
					className={`px-3 py-1.5 text-sm font-medium ${
						viewMode === "calendar"
							? "bg-blue-600 text-white"
							: "bg-white text-gray-700 hover:bg-gray-50"
					}`}
				>
					Calendar
				</button>
				<button
					type="button"
					onClick={() => onViewModeChange("table")}
					className={`px-3 py-1.5 text-sm font-medium border-l border-gray-300 ${
						viewMode === "table"
							? "bg-blue-600 text-white"
							: "bg-white text-gray-700 hover:bg-gray-50"
					}`}
				>
					Table
				</button>
			</div>

			{/* Add Entry button */}
			<button
				type="button"
				onClick={onAddEntry}
				className="ml-2 px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
			>
				Add Entry
			</button>
		</div>
	</div>
	);
}
