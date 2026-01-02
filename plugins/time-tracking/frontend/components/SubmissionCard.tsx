// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import { submissionsApi, type SubmissionListItem } from "../api";
import type { CompanyInfo } from "../types";

interface SubmissionCardProps {
	companies: CompanyInfo[];
	currentDate: Date;
	onOpenFullPanel: () => void;
}

/**
 * SubmissionCard - Compact sidebar card for timesheet submissions
 *
 * Shows submission status and quick access to the full submission form.
 */
export function SubmissionCard({
	companies,
	currentDate,
	onOpenFullPanel,
}: SubmissionCardProps) {
	const [submissions, setSubmissions] = useState<SubmissionListItem[]>([]);
	const [isLoading, setIsLoading] = useState(true);

	const monthName = currentDate.toLocaleDateString("en-US", {
		month: "short",
		year: "numeric",
	});

	// Load recent submissions
	const loadSubmissions = useCallback(async () => {
		setIsLoading(true);
		try {
			const response = await submissionsApi.list({ limit: 3 });
			setSubmissions(response.submissions);
		} catch (err) {
			console.error("Failed to load submissions:", err);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		loadSubmissions();
	}, [loadSubmissions]);

	const getCompanyName = (companyId: string) => {
		return companies.find((c) => c.id === companyId)?.name || "Unknown";
	};

	const getStatusColor = (status: string) => {
		switch (status) {
			case "sent":
				return "text-green-600";
			case "pending":
				return "text-yellow-600";
			case "failed":
				return "text-red-600";
			default:
				return "text-gray-600";
		}
	};

	// Check if current month has been submitted for any company
	const currentMonthSubmissions = submissions.filter((s) => {
		const subDate = new Date(s.period_start);
		return (
			subDate.getFullYear() === currentDate.getFullYear() &&
			subDate.getMonth() === currentDate.getMonth()
		);
	});

	return (
		<div className="bg-white rounded-lg shadow p-4">
			<div className="flex items-center justify-between mb-3">
				<h3 className="text-sm font-semibold text-gray-900">Submissions</h3>
				<span className="text-xs text-gray-500">{monthName}</span>
			</div>

			{/* Current month status */}
			<div className="mb-3">
				{currentMonthSubmissions.length > 0 ? (
					<div className="space-y-1">
						{currentMonthSubmissions.map((sub) => (
							<div
								key={sub.id}
								className="flex items-center justify-between text-sm"
							>
								<span className="text-gray-700 truncate">
									{getCompanyName(sub.company_id)}
								</span>
								<span className={`text-xs font-medium ${getStatusColor(sub.status)}`}>
									{sub.status}
								</span>
							</div>
						))}
					</div>
				) : (
					<p className="text-sm text-gray-500">
						No submissions for {monthName}
					</p>
				)}
			</div>

			{/* Submit button */}
			<button
				type="button"
				onClick={onOpenFullPanel}
				className="w-full px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
			>
				Submit Timesheet
			</button>

			{/* Recent history */}
			{!isLoading && submissions.length > 0 && (
				<div className="mt-3 pt-3 border-t border-gray-100">
					<p className="text-xs font-medium text-gray-500 mb-2">Recent</p>
					<div className="space-y-1">
						{submissions.slice(0, 2).map((sub) => (
							<div key={sub.id} className="flex items-center justify-between text-xs">
								<span className="text-gray-600 truncate">
									{new Date(sub.period_start).toLocaleDateString("en-US", {
										month: "short",
										year: "numeric",
									})}
								</span>
								<span className={getStatusColor(sub.status)}>{sub.status}</span>
							</div>
						))}
					</div>
				</div>
			)}
		</div>
	);
}
