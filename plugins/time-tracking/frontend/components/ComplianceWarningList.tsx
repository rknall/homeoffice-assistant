// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import type { ComplianceWarning } from "../types";
import { WARNING_LEVEL_COLORS } from "../types";

interface ComplianceWarningListProps {
	warnings: ComplianceWarning[];
}

/** Render compliance warnings returned by the server for a time entry. */
export function ComplianceWarningList({ warnings }: ComplianceWarningListProps) {
	if (warnings.length === 0) return null;
	return (
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
	);
}
