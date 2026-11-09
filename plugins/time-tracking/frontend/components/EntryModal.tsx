// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type {
	CompanyInfo,
	ComplianceWarning,
	TimeEntry,
	TimeEntryCreate,
	TimeEntryUpdate,
} from "../types";
import { TimeRecordForm } from "./TimeRecordForm";

interface EntryModalProps {
	selectedDate: string;
	selectedEntry: TimeEntry | null;
	companies: CompanyInfo[];
	warnings: ComplianceWarning[];
	isSaving: boolean;
	onSubmit: (data: TimeEntryCreate | TimeEntryUpdate) => Promise<void>;
	onCancel: () => void;
}

/** Modal that hosts the time entry form for a new or existing entry. */
export function EntryModal({
	selectedDate,
	selectedEntry,
	companies,
	warnings,
	isSaving,
	onSubmit,
	onCancel,
}: EntryModalProps) {
	return (
	<div className="fixed inset-0 z-50 overflow-y-auto">
		<div className="flex min-h-screen items-center justify-center p-4">
			{/* Backdrop */}
			<button
				type="button"
				className="fixed inset-0 bg-black bg-opacity-25 cursor-default"
				onClick={onCancel}
				onKeyDown={(e) => e.key === "Escape" && onCancel()}
				aria-label="Close modal"
			/>

			{/* Modal */}
			<div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
				<h2 className="text-lg font-medium text-gray-900 mb-4">
					{selectedEntry ? "Edit Time Entry" : "New Time Entry"}
				</h2>
				<TimeRecordForm
					entry={selectedEntry}
					companyId={selectedEntry?.company_id || companies[0]?.id || ""}
					date={selectedDate}
					onSubmit={onSubmit}
					onCancel={onCancel}
					warnings={warnings}
					isLoading={isSaving}
					companies={companies}
					preselectedCompanyId={selectedEntry?.company_id || undefined}
				/>
			</div>
		</div>
	</div>
	);
}
