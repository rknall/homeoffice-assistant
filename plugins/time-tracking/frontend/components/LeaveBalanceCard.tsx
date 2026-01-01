// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import { leaveBalanceApi } from "../api";
import type { CompanyInfo, LeaveBalanceResponse } from "../types";

interface LeaveBalanceCardProps {
	companies: CompanyInfo[];
	currentDate: Date;
}

/**
 * LeaveBalanceCard - Shows vacation and comp time balances
 *
 * Displays leave balances for all companies or a selected company,
 * showing entitled days, used days, and remaining balance.
 */
export function LeaveBalanceCard({
	companies,
	currentDate,
}: LeaveBalanceCardProps) {
	const [balances, setBalances] = useState<
		Map<string, LeaveBalanceResponse>
	>(new Map());
	const [isLoading, setIsLoading] = useState(true);
	const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(
		null,
	);

	// Load balances for all companies
	const loadBalances = useCallback(async () => {
		if (companies.length === 0) return;

		setIsLoading(true);
		const year = currentDate.getFullYear();
		const newBalances = new Map<string, LeaveBalanceResponse>();

		try {
			// Load balances for all companies in parallel
			const results = await Promise.all(
				companies.map(async (company) => {
					try {
						const balance = await leaveBalanceApi.get(company.id, year);
						return { companyId: company.id, balance };
					} catch {
						return { companyId: company.id, balance: null };
					}
				}),
			);

			for (const result of results) {
				if (result.balance) {
					newBalances.set(result.companyId, result.balance);
				}
			}

			setBalances(newBalances);
		} catch (err) {
			console.error("Failed to load leave balances:", err);
		} finally {
			setIsLoading(false);
		}
	}, [companies, currentDate]);

	useEffect(() => {
		loadBalances();
	}, [loadBalances]);

	// Initialize selected company
	useEffect(() => {
		if (companies.length > 0 && selectedCompanyId === null) {
			setSelectedCompanyId(companies[0].id);
		}
	}, [companies, selectedCompanyId]);

	// Get company name
	const getCompanyName = (companyId: string): string => {
		const company = companies.find((c) => c.id === companyId);
		return company?.name || "Unknown";
	};

	// Get company color
	const getCompanyColor = (companyId: string): string => {
		const company = companies.find((c) => c.id === companyId);
		return company?.color || "#3B82F6";
	};

	// Calculate totals across all companies or for selected company
	const displayBalance = selectedCompanyId
		? balances.get(selectedCompanyId)
		: null;

	// Calculate aggregate totals for "All Companies" view
	const aggregateTotals = {
		vacation: {
			entitled: 0,
			used: 0,
			pending: 0,
			available: 0,
		},
		compTime: {
			entitled: 0,
			used: 0,
			pending: 0,
			available: 0,
		},
	};

	if (!selectedCompanyId) {
		for (const balance of balances.values()) {
			if (balance.vacation) {
				aggregateTotals.vacation.entitled +=
					balance.vacation.entitled_days + balance.vacation.carried_over;
				aggregateTotals.vacation.used += balance.vacation.used_days;
				aggregateTotals.vacation.pending += balance.vacation.pending_days;
				aggregateTotals.vacation.available += balance.vacation.available_days;
			}
			if (balance.comp_time) {
				aggregateTotals.compTime.entitled +=
					balance.comp_time.entitled_days + balance.comp_time.carried_over;
				aggregateTotals.compTime.used += balance.comp_time.used_days;
				aggregateTotals.compTime.pending += balance.comp_time.pending_days;
				aggregateTotals.compTime.available += balance.comp_time.available_days;
			}
		}
	}

	return (
		<div className="bg-white rounded-lg shadow p-4">
			<div className="flex items-center justify-between mb-3">
				<h3 className="text-sm font-semibold text-gray-900">Leave Balance</h3>
				<span className="text-xs text-gray-500">
					{currentDate.getFullYear()}
				</span>
			</div>

			{/* Company selector */}
			{companies.length > 1 && (
				<div className="mb-3">
					<select
						value={selectedCompanyId || ""}
						onChange={(e) =>
							setSelectedCompanyId(e.target.value || null)
						}
						className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5"
					>
						<option value="">All Companies</option>
						{companies.map((company) => (
							<option key={company.id} value={company.id}>
								{company.name}
							</option>
						))}
					</select>
				</div>
			)}

			{isLoading ? (
				<div className="text-sm text-gray-500 text-center py-4">
					Loading...
				</div>
			) : balances.size === 0 ? (
				<div className="text-sm text-gray-500 text-center py-4">
					No leave balances configured
				</div>
			) : (
				<div className="space-y-4">
					{/* Vacation balance */}
					<BalanceSection
						title="Vacation"
						entitled={
							selectedCompanyId && displayBalance?.vacation
								? displayBalance.vacation.entitled_days +
									displayBalance.vacation.carried_over
								: aggregateTotals.vacation.entitled
						}
						used={
							selectedCompanyId && displayBalance?.vacation
								? displayBalance.vacation.used_days
								: aggregateTotals.vacation.used
						}
						pending={
							selectedCompanyId && displayBalance?.vacation
								? displayBalance.vacation.pending_days
								: aggregateTotals.vacation.pending
						}
						available={
							selectedCompanyId && displayBalance?.vacation
								? displayBalance.vacation.available_days
								: aggregateTotals.vacation.available
						}
						color={
							selectedCompanyId
								? getCompanyColor(selectedCompanyId)
								: "#3B82F6"
						}
						hasData={
							selectedCompanyId
								? !!displayBalance?.vacation
								: aggregateTotals.vacation.entitled > 0
						}
					/>

					{/* Comp Time balance */}
					<BalanceSection
						title="Comp Time"
						entitled={
							selectedCompanyId && displayBalance?.comp_time
								? displayBalance.comp_time.entitled_days +
									displayBalance.comp_time.carried_over
								: aggregateTotals.compTime.entitled
						}
						used={
							selectedCompanyId && displayBalance?.comp_time
								? displayBalance.comp_time.used_days
								: aggregateTotals.compTime.used
						}
						pending={
							selectedCompanyId && displayBalance?.comp_time
								? displayBalance.comp_time.pending_days
								: aggregateTotals.compTime.pending
						}
						available={
							selectedCompanyId && displayBalance?.comp_time
								? displayBalance.comp_time.available_days
								: aggregateTotals.compTime.available
						}
						color={
							selectedCompanyId
								? getCompanyColor(selectedCompanyId)
								: "#10B981"
						}
						hasData={
							selectedCompanyId
								? !!displayBalance?.comp_time
								: aggregateTotals.compTime.entitled > 0
						}
					/>
				</div>
			)}
		</div>
	);
}

interface BalanceSectionProps {
	title: string;
	entitled: number;
	used: number;
	pending: number;
	available: number;
	color: string;
	hasData: boolean;
}

function BalanceSection({
	title,
	entitled,
	used,
	pending,
	available,
	color,
	hasData,
}: BalanceSectionProps) {
	if (!hasData) {
		return (
			<div className="text-sm text-gray-400">
				<span className="font-medium">{title}:</span> Not configured
			</div>
		);
	}

	const usedPercent = entitled > 0 ? (used / entitled) * 100 : 0;
	const pendingPercent = entitled > 0 ? (pending / entitled) * 100 : 0;

	return (
		<div>
			<div className="flex items-center justify-between mb-1">
				<span className="text-sm font-medium text-gray-700">{title}</span>
				<span className="text-sm font-semibold" style={{ color }}>
					{available} days
				</span>
			</div>

			{/* Progress bar */}
			<div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-1">
				<div className="h-full flex">
					<div
						className="h-full transition-all"
						style={{
							width: `${usedPercent}%`,
							backgroundColor: color,
						}}
					/>
					<div
						className="h-full transition-all opacity-50"
						style={{
							width: `${pendingPercent}%`,
							backgroundColor: color,
						}}
					/>
				</div>
			</div>

			{/* Details */}
			<div className="flex justify-between text-xs text-gray-500">
				<span>
					Used: {used}
					{pending > 0 && ` (+${pending} pending)`}
				</span>
				<span>of {entitled}</span>
			</div>
		</div>
	);
}
