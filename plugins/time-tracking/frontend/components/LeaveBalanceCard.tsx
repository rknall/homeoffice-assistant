// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import { leaveBalanceApi } from "../api";
import type { LeaveBalanceResponse } from "../types";

interface LeaveBalanceCardProps {
	currentDate: Date;
}

/**
 * LeaveBalanceCard - Shows vacation, comp time, and sick days
 *
 * Displays system-wide leave balances showing entitled days,
 * used days, and remaining balance.
 */
export function LeaveBalanceCard({ currentDate }: LeaveBalanceCardProps) {
	const [balance, setBalance] = useState<LeaveBalanceResponse | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const loadBalance = useCallback(async () => {
		setIsLoading(true);
		setError(null);
		const year = currentDate.getFullYear();

		try {
			const data = await leaveBalanceApi.get(year);
			setBalance(data);
		} catch (err) {
			console.error("Failed to load leave balance:", err);
			setError("Failed to load");
		} finally {
			setIsLoading(false);
		}
	}, [currentDate]);

	useEffect(() => {
		loadBalance();
	}, [loadBalance]);

	// Use the backend-calculated vacation_remaining directly
	// vacation_remaining = entitled + carryover - taken - planned
	const vacationTotalRemaining = balance?.vacation_remaining ?? 0;

	return (
		<div className="bg-white rounded-lg shadow p-4">
			<div className="flex items-center justify-between mb-3">
				<h3 className="text-sm font-semibold text-gray-900">Leave Balance</h3>
				<span className="text-xs text-gray-500">
					{currentDate.getFullYear()}
				</span>
			</div>

			{isLoading ? (
				<div className="text-sm text-gray-500 text-center py-4">Loading...</div>
			) : error ? (
				<div className="text-sm text-red-500 text-center py-4">{error}</div>
			) : balance ? (
				<div className="space-y-4">
					{/* Vacation balance */}
					<div>
						<div className="flex items-center justify-between mb-1">
							<span className="text-sm font-medium text-gray-700">
								Vacation
							</span>
							<span className="text-sm font-semibold text-blue-600">
								{vacationTotalRemaining} days
							</span>
						</div>

						{/* Details - Used / Planned */}
						<div className="flex items-center justify-between mb-1">
							<span className="text-xs font-medium text-gray-500">
								Used / Planned:
							</span>
							<span className="text-xs font-semibold text-blue-600">
								{balance.vacation_taken} / {balance.vacation_planned}
							</span>
						</div>
					</div>

					{/* Comp Time balance */}
					<div>
						<div className="flex items-center justify-between mb-1">
							<span className="text-sm font-medium text-gray-700">
								Comp Time
							</span>
							<span
								className={`text-sm font-semibold ${
									balance.comp_time_balance >= 0
										? "text-green-600"
										: "text-red-600"
								}`}
							>
								{balance.comp_time_balance.toFixed(1)}h
							</span>
						</div>

						{/* Simple bar showing positive/negative */}
						<div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-1 relative">
							<div className="absolute inset-y-0 left-1/2 w-px bg-gray-300" />
							{balance.comp_time_balance !== 0 && (
								<div
									className={`h-full transition-all ${
										balance.comp_time_balance >= 0
											? "bg-green-500"
											: "bg-red-500"
									}`}
									style={{
										width: `${Math.min(Math.abs(balance.comp_time_balance) * 2, 50)}%`,
										marginLeft:
											balance.comp_time_balance >= 0 ? "50%" : undefined,
										marginRight:
											balance.comp_time_balance < 0 ? "50%" : undefined,
										float: balance.comp_time_balance < 0 ? "right" : undefined,
									}}
								/>
							)}
						</div>
					</div>

					{/* Sick Days */}
					<div>
						<div className="flex items-center justify-between">
							<span className="text-sm font-medium text-gray-700">
								Sick Days
							</span>
							<span className="text-sm font-semibold text-red-600">
								{balance.sick_days_taken} days
							</span>
						</div>
						<div className="text-xs text-gray-500">Used this year</div>
					</div>
				</div>
			) : (
				<div className="text-sm text-gray-400 text-center py-4">
					No data available
				</div>
			)}
		</div>
	);
}
