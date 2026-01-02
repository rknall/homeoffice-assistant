// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import {
	submissionsApi,
	type SubmissionListItem,
	type SubmissionResponse,
} from "../api";
import type { CompanyInfo } from "../types";

interface MonthlySubmissionPanelProps {
	companies: CompanyInfo[];
	currentDate: Date;
}

/**
 * MonthlySubmissionPanel - Submit and track monthly timesheet submissions
 *
 * Allows users to submit timesheets for a specific company and month,
 * and view the history of previous submissions.
 */
export function MonthlySubmissionPanel({
	companies,
	currentDate,
}: MonthlySubmissionPanelProps) {
	const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
	const [recipientEmail, setRecipientEmail] = useState<string>("");
	const [notes, setNotes] = useState<string>("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [submissionResult, setSubmissionResult] =
		useState<SubmissionResponse | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [submissions, setSubmissions] = useState<SubmissionListItem[]>([]);
	const [isLoadingHistory, setIsLoadingHistory] = useState(false);

	const year = currentDate.getFullYear();
	const month = currentDate.getMonth() + 1;
	const monthName = currentDate.toLocaleDateString("en-US", {
		month: "long",
		year: "numeric",
	});

	// Load submission history
	const loadSubmissions = useCallback(async () => {
		setIsLoadingHistory(true);
		try {
			const response = await submissionsApi.list({
				companyId: selectedCompanyId || undefined,
				limit: 10,
			});
			setSubmissions(response.submissions);
		} catch (err) {
			console.error("Failed to load submissions:", err);
		} finally {
			setIsLoadingHistory(false);
		}
	}, [selectedCompanyId]);

	useEffect(() => {
		loadSubmissions();
	}, [loadSubmissions]);

	// Set default company when companies load
	useEffect(() => {
		if (companies.length > 0 && !selectedCompanyId) {
			setSelectedCompanyId(companies[0].id);
		}
	}, [companies, selectedCompanyId]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		if (!selectedCompanyId) {
			setError("Please select a company");
			return;
		}

		if (!recipientEmail) {
			setError("Please enter a recipient email");
			return;
		}

		setIsSubmitting(true);
		setError(null);
		setSubmissionResult(null);

		try {
			const result = await submissionsApi.submit({
				companyId: selectedCompanyId,
				year,
				month,
				recipientEmail,
				notes: notes || undefined,
			});
			setSubmissionResult(result);
			setNotes("");
			// Reload submissions after successful submit
			await loadSubmissions();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Submission failed");
		} finally {
			setIsSubmitting(false);
		}
	};

	const getStatusBadge = (status: string) => {
		const styles: Record<string, string> = {
			sent: "bg-green-100 text-green-800",
			pending: "bg-yellow-100 text-yellow-800",
			failed: "bg-red-100 text-red-800",
		};
		return (
			<span
				className={`px-2 py-0.5 text-xs font-medium rounded-full ${styles[status] || "bg-gray-100 text-gray-800"}`}
			>
				{status}
			</span>
		);
	};

	const getCompanyName = (companyId: string) => {
		return companies.find((c) => c.id === companyId)?.name || "Unknown";
	};

	return (
		<div className="bg-white rounded-lg border border-gray-200 p-6">
			<h2 className="text-lg font-semibold text-gray-900 mb-4">
				Submit Timesheet
			</h2>

			<form onSubmit={handleSubmit} className="space-y-4">
				{/* Period display */}
				<div>
					<label
						htmlFor="period-display"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Period
					</label>
					<div
						id="period-display"
						className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-md text-gray-900"
					>
						{monthName}
					</div>
				</div>

				{/* Company selection */}
				<div>
					<label
						htmlFor="company-select"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Company
					</label>
					<select
						id="company-select"
						value={selectedCompanyId}
						onChange={(e) => setSelectedCompanyId(e.target.value)}
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
					>
						{companies.map((company) => (
							<option key={company.id} value={company.id}>
								{company.name}
							</option>
						))}
					</select>
				</div>

				{/* Recipient email */}
				<div>
					<label
						htmlFor="recipient-email"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Send to Email
					</label>
					<input
						id="recipient-email"
						type="email"
						value={recipientEmail}
						onChange={(e) => setRecipientEmail(e.target.value)}
						placeholder="hr@company.com"
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
						required
					/>
				</div>

				{/* Notes */}
				<div>
					<label
						htmlFor="submission-notes"
						className="block text-sm font-medium text-gray-700 mb-1"
					>
						Notes (optional)
					</label>
					<textarea
						id="submission-notes"
						value={notes}
						onChange={(e) => setNotes(e.target.value)}
						rows={2}
						placeholder="Any additional notes..."
						className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
					/>
				</div>

				{/* Error message */}
				{error && (
					<div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
						{error}
					</div>
				)}

				{/* Success message */}
				{submissionResult && (
					<div className="p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm">
						<p className="font-medium">Timesheet submitted</p>
						<p>Status: {submissionResult.status}</p>
						<p>Sent to: {submissionResult.sent_to}</p>
						<p>Records included: {submissionResult.record_count}</p>
					</div>
				)}

				{/* Submit button */}
				<button
					type="submit"
					disabled={isSubmitting || !selectedCompanyId || !recipientEmail}
					className="w-full px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
				>
					{isSubmitting ? "Submitting..." : "Submit Timesheet"}
				</button>
			</form>

			{/* Submission History */}
			<div className="mt-8">
				<h3 className="text-sm font-semibold text-gray-900 mb-3">
					Recent Submissions
				</h3>
				{isLoadingHistory ? (
					<p className="text-sm text-gray-500">Loading...</p>
				) : submissions.length === 0 ? (
					<p className="text-sm text-gray-500">No submissions yet</p>
				) : (
					<div className="space-y-2">
						{submissions.map((submission) => (
							<div
								key={submission.id}
								className="p-3 bg-gray-50 rounded-md text-sm"
							>
								<div className="flex items-center justify-between">
									<span className="font-medium">
										{getCompanyName(submission.company_id)}
									</span>
									{getStatusBadge(submission.status)}
								</div>
								<div className="text-gray-500 text-xs mt-1">
									{new Date(submission.period_start).toLocaleDateString()} -{" "}
									{new Date(submission.period_end).toLocaleDateString()}
								</div>
								<div className="text-gray-500 text-xs">
									Sent to: {submission.sent_to_email}
								</div>
								<div className="text-gray-400 text-xs">
									{new Date(submission.submitted_at).toLocaleString()}
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
