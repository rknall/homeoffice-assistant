// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import {
	formatHours,
	getWeekEnd,
	getWeekStart,
	leaveBalanceApi,
	timeEntriesApi,
	toISODateString,
} from "../api";
import type {
	ComplianceWarning,
	LeaveBalance,
	TimeEntry,
	TimeEntryCreate,
	TimeEntryUpdate,
} from "../types";
import { TimeRecordForm } from "./TimeRecordForm";
import { WeekView } from "./WeekView";

interface TimeTrackingPageProps {
	companyId: string;
	companyName: string;
}

export function TimeTrackingPage({
	companyId,
	companyName,
}: TimeTrackingPageProps) {
	const [currentDate, setCurrentDate] = useState(new Date());
	const [entries, setEntries] = useState<TimeEntry[]>([]);
	const [vacationBalance, setVacationBalance] = useState<LeaveBalance | null>(
		null,
	);
	const [compTimeBalance, setCompTimeBalance] = useState<LeaveBalance | null>(
		null,
	);
	const [selectedDate, setSelectedDate] = useState<string | null>(null);
	const [selectedEntry, setSelectedEntry] = useState<TimeEntry | null>(null);
	const [formWarnings, setFormWarnings] = useState<ComplianceWarning[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [isSaving, setIsSaving] = useState(false);
	const [todayEntries, setTodayEntries] = useState<TimeEntry[]>([]);

	const loadEntries = useCallback(async () => {
		setIsLoading(true);
		try {
			const weekStart = getWeekStart(currentDate);
			const weekEnd = getWeekEnd(currentDate);

			const response = await timeEntriesApi.list({
				company_id: companyId,
				start_date: toISODateString(weekStart),
				end_date: toISODateString(weekEnd),
			});
			setEntries(response);
		} catch (err) {
			console.error("Failed to load entries:", err);
		} finally {
			setIsLoading(false);
		}
	}, [companyId, currentDate]);

	const loadBalances = useCallback(async () => {
		try {
			const balances = await leaveBalanceApi.get(companyId);
			setVacationBalance(balances.vacation);
			setCompTimeBalance(balances.comp_time);
		} catch (err) {
			console.error("Failed to load balances:", err);
		}
	}, [companyId]);

	const loadTodayEntries = useCallback(async () => {
		try {
			const allToday = await timeEntriesApi.getToday();
			// Filter to just this company's entries
			const companyToday = allToday.filter((e) => e.company_id === companyId);
			setTodayEntries(companyToday);
		} catch (err) {
			console.error("Failed to load today entries:", err);
		}
	}, [companyId]);

	useEffect(() => {
		loadEntries();
	}, [loadEntries]);

	useEffect(() => {
		loadBalances();
		loadTodayEntries();
	}, [loadBalances, loadTodayEntries]);

	// Find active (open) entry for today
	const activeEntry = todayEntries.find(
		(e) => e.is_open && e.entry_type === "work",
	);

	const handleCheckIn = useCallback(async () => {
		try {
			await timeEntriesApi.checkIn({ company_id: companyId });
			await loadTodayEntries();
			await loadEntries();
		} catch (err) {
			console.error("Check-in failed:", err);
		}
	}, [companyId, loadEntries, loadTodayEntries]);

	const handleCheckOut = useCallback(async () => {
		if (!activeEntry) return;
		try {
			await timeEntriesApi.checkOut();
			await loadTodayEntries();
			await loadEntries();
		} catch (err) {
			console.error("Check-out failed:", err);
		}
	}, [activeEntry, loadEntries, loadTodayEntries]);

	// Keyboard shortcuts
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			// Ctrl/Cmd + I for check-in
			if ((e.ctrlKey || e.metaKey) && e.key === "i") {
				e.preventDefault();
				handleCheckIn();
			}
			// Ctrl/Cmd + O for check-out
			if ((e.ctrlKey || e.metaKey) && e.key === "o") {
				e.preventDefault();
				handleCheckOut();
			}
			// Escape to close form
			if (e.key === "Escape" && selectedDate) {
				setSelectedDate(null);
				setSelectedEntry(null);
				setFormWarnings([]);
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [selectedDate, handleCheckIn, handleCheckOut]);

	const handleDayClick = (date: string, dayEntries?: TimeEntry[]) => {
		setSelectedDate(date);
		// If there's exactly one entry, select it for editing; otherwise create new
		setSelectedEntry(dayEntries?.length === 1 ? dayEntries[0] : null);
		setFormWarnings([]);
	};

	const handleFormSubmit = async (data: TimeEntryCreate | TimeEntryUpdate) => {
		setIsSaving(true);
		try {
			if (selectedEntry) {
				await timeEntriesApi.update(selectedEntry.id, data as TimeEntryUpdate);
			} else {
				await timeEntriesApi.create(data as TimeEntryCreate);
			}

			// Close the form and reload data
			setSelectedDate(null);
			setSelectedEntry(null);
			setFormWarnings([]);
			await loadEntries();
			await loadBalances();
			await loadTodayEntries();
		} catch (err) {
			console.error("Failed to save entry:", err);
		} finally {
			setIsSaving(false);
		}
	};

	const handleFormCancel = () => {
		setSelectedDate(null);
		setSelectedEntry(null);
		setFormWarnings([]);
	};

	// Check-in/out state based on whether there's an active (open) entry
	const canCheckIn = !activeEntry;
	const canCheckOut = !!activeEntry;

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold text-gray-900">Time Tracking</h1>
					<p className="text-sm text-gray-500">{companyName}</p>
				</div>

				{/* Quick actions */}
				<div className="flex items-center gap-3">
					{canCheckIn && (
						<button
							type="button"
							onClick={handleCheckIn}
							className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
							title="Keyboard: Ctrl+I"
						>
							Check In
						</button>
					)}
					{canCheckOut && (
						<button
							type="button"
							onClick={handleCheckOut}
							className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700"
							title="Keyboard: Ctrl+O"
						>
							Check Out
						</button>
					)}
				</div>
			</div>

			{/* Leave balances */}
			<div className="grid grid-cols-2 gap-4">
				{vacationBalance && (
					<div className="bg-white rounded-lg shadow p-4">
						<h3 className="text-sm font-medium text-gray-500">
							Vacation Balance
						</h3>
						<div className="mt-1 flex items-baseline gap-2">
							<span className="text-2xl font-bold text-gray-900">
								{vacationBalance.available_days}
							</span>
							<span className="text-sm text-gray-500">days available</span>
						</div>
						<p className="mt-1 text-xs text-gray-400">
							{vacationBalance.used_days} used / {vacationBalance.entitled_days}{" "}
							entitled
							{vacationBalance.carried_over > 0 &&
								` + ${vacationBalance.carried_over} carried over`}
						</p>
					</div>
				)}
				{compTimeBalance && (
					<div className="bg-white rounded-lg shadow p-4">
						<h3 className="text-sm font-medium text-gray-500">
							Comp Time Balance
						</h3>
						<div className="mt-1 flex items-baseline gap-2">
							<span className="text-2xl font-bold text-gray-900">
								{formatHours(compTimeBalance.available_days * 8)}
							</span>
							<span className="text-sm text-gray-500">available</span>
						</div>
						<p className="mt-1 text-xs text-gray-400">
							{formatHours(compTimeBalance.entitled_days * 8)} accrued,{" "}
							{formatHours(compTimeBalance.used_days * 8)} used
						</p>
					</div>
				)}
			</div>

			{/* Week view */}
			<WeekView
				entries={entries}
				currentDate={currentDate}
				onDateChange={setCurrentDate}
				onDayClick={handleDayClick}
				isLoading={isLoading}
			/>

			{/* Time entry form modal */}
			{selectedDate && (
				<div className="fixed inset-0 z-50 overflow-y-auto">
					<div className="flex min-h-screen items-center justify-center p-4">
						{/* Backdrop */}
						<button
							type="button"
							className="fixed inset-0 bg-black bg-opacity-25 cursor-default"
							onClick={handleFormCancel}
							onKeyDown={(e) => e.key === "Escape" && handleFormCancel()}
							aria-label="Close modal"
						/>

						{/* Modal */}
						<div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
							<h2 className="text-lg font-medium text-gray-900 mb-4">
								{selectedEntry ? "Edit Time Entry" : "New Time Entry"}
							</h2>
							<TimeRecordForm
								entry={selectedEntry}
								companyId={companyId}
								date={selectedDate}
								onSubmit={handleFormSubmit}
								onCancel={handleFormCancel}
								warnings={formWarnings}
								isLoading={isSaving}
							/>
						</div>
					</div>
				</div>
			)}

			{/* Keyboard shortcuts help */}
			<div className="text-xs text-gray-400 text-center">
				Keyboard shortcuts:{" "}
				<kbd className="px-1 py-0.5 bg-gray-100 rounded">Ctrl+I</kbd> Check In,{" "}
				<kbd className="px-1 py-0.5 bg-gray-100 rounded">Ctrl+O</kbd> Check Out,{" "}
				<kbd className="px-1 py-0.5 bg-gray-100 rounded">Esc</kbd> Close form
			</div>
		</div>
	);
}
