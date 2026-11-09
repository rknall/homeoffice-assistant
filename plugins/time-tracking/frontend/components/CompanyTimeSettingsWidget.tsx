// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from "react";
import { companySettingsApi, errorMessage } from "../api";
import type { CompanyTimeSettings, CompanyTimeSettingsUpdate } from "../types";

interface CompanyTimeSettingsWidgetProps {
	companyId: string;
}

type SettingsForm = Required<
	Omit<CompanyTimeSettingsUpdate, "default_timesheet_contact_id">
>;

const COUNTRY_OPTIONS = [
	{ code: "AT", name: "Austria" },
	{ code: "DE", name: "Germany" },
	{ code: "CH", name: "Switzerland" },
];

// Defaults match CompanyTimeSettingsBase in the plugin backend schemas.
const DEFAULT_FORM: SettingsForm = {
	timezone: "Europe/Vienna",
	country_code: "AT",
	vacation_days_per_year: 25,
	daily_overtime_threshold: 8,
	weekly_overtime_threshold: 40,
	overtime_threshold_hours: 0,
	comp_time_warning_balance: 40,
	lock_period_days: 7,
};

type NumericKey = Exclude<keyof SettingsForm, "timezone" | "country_code">;

const NUMBER_FIELDS: {
	key: NumericKey;
	label: string;
	unit: string;
	step: string;
}[] = [
	{
		key: "vacation_days_per_year",
		label: "Vacation days per year",
		unit: "days",
		step: "0.5",
	},
	{
		key: "daily_overtime_threshold",
		label: "Daily overtime threshold",
		unit: "h",
		step: "0.5",
	},
	{
		key: "weekly_overtime_threshold",
		label: "Weekly overtime threshold",
		unit: "h",
		step: "0.5",
	},
	{
		key: "overtime_threshold_hours",
		label: "Overtime threshold hours",
		unit: "h",
		step: "0.5",
	},
	{
		key: "comp_time_warning_balance",
		label: "Comp time warning balance",
		unit: "h",
		step: "0.5",
	},
	{
		key: "lock_period_days",
		label: "Lock period",
		unit: "days",
		step: "1",
	},
];

function toForm(settings: CompanyTimeSettings): SettingsForm {
	return {
		timezone: settings.timezone,
		country_code: settings.country_code,
		vacation_days_per_year: settings.vacation_days_per_year,
		daily_overtime_threshold: settings.daily_overtime_threshold,
		weekly_overtime_threshold: settings.weekly_overtime_threshold,
		overtime_threshold_hours: settings.overtime_threshold_hours,
		comp_time_warning_balance: settings.comp_time_warning_balance,
		lock_period_days: settings.lock_period_days,
	};
}

const INPUT_CLASS =
	"w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500";

/**
 * CompanyTimeSettingsWidget - View and edit a company's time tracking settings.
 *
 * Rendered on the company detail page through the plugin's companyDetail
 * widget slot. The fields mirror the plugin backend's company settings schema.
 */
export function CompanyTimeSettingsWidget({
	companyId,
}: CompanyTimeSettingsWidgetProps) {
	const [settings, setSettings] = useState<CompanyTimeSettings | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isEditing, setIsEditing] = useState(false);
	const [isSaving, setIsSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [formData, setFormData] = useState<SettingsForm>(DEFAULT_FORM);

	const loadSettings = useCallback(async () => {
		setIsLoading(true);
		setError(null);
		try {
			const data = await companySettingsApi.get(companyId);
			setSettings(data);
			setFormData(data ? toForm(data) : DEFAULT_FORM);
		} catch (err) {
			setError(errorMessage(err, "Failed to load settings"));
		} finally {
			setIsLoading(false);
		}
	}, [companyId]);

	useEffect(() => {
		loadSettings();
	}, [loadSettings]);

	const handleSave = async () => {
		setIsSaving(true);
		setError(null);
		try {
			const saved = settings
				? await companySettingsApi.update(companyId, formData)
				: await companySettingsApi.create(companyId, formData);
			setSettings(saved);
			setFormData(toForm(saved));
			setIsEditing(false);
		} catch (err) {
			setError(errorMessage(err, "Failed to save settings"));
		} finally {
			setIsSaving(false);
		}
	};

	const handleCancel = () => {
		setFormData(settings ? toForm(settings) : DEFAULT_FORM);
		setIsEditing(false);
		setError(null);
	};

	const setNumber = (key: NumericKey, raw: string) => {
		const value = Number.parseFloat(raw);
		setFormData({ ...formData, [key]: Number.isNaN(value) ? 0 : value });
	};

	if (isLoading) {
		return (
			<div className="bg-white rounded-lg shadow p-6">
				<h3 className="text-lg font-medium text-gray-900 mb-4">
					Time Tracking Settings
				</h3>
				<div className="animate-pulse space-y-3">
					<div className="h-4 bg-gray-200 rounded w-1/2" />
					<div className="h-4 bg-gray-200 rounded w-1/3" />
				</div>
			</div>
		);
	}

	return (
		<div className="bg-white rounded-lg shadow">
			<div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
				<h3 className="text-lg font-medium text-gray-900">
					Time Tracking Settings
				</h3>
				{!isEditing && (
					<button
						type="button"
						onClick={() => setIsEditing(true)}
						className="text-sm text-blue-600 hover:text-blue-800"
					>
						{settings ? "Edit" : "Configure"}
					</button>
				)}
			</div>

			<div className="p-6">
				{error && (
					<div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200">
						<p className="text-sm text-red-700">{error}</p>
					</div>
				)}

				{isEditing ? (
					<form
						onSubmit={(e) => {
							e.preventDefault();
							handleSave();
						}}
						className="space-y-4"
					>
						<div className="grid grid-cols-2 gap-4">
							<div>
								<label
									htmlFor="tt-country"
									className="block text-sm font-medium text-gray-700 mb-1"
								>
									Country
								</label>
								<select
									id="tt-country"
									value={formData.country_code}
									onChange={(e) =>
										setFormData({ ...formData, country_code: e.target.value })
									}
									className={INPUT_CLASS}
								>
									{COUNTRY_OPTIONS.map((country) => (
										<option key={country.code} value={country.code}>
											{country.name}
										</option>
									))}
								</select>
							</div>
							<div>
								<label
									htmlFor="tt-timezone"
									className="block text-sm font-medium text-gray-700 mb-1"
								>
									Timezone
								</label>
								<input
									type="text"
									id="tt-timezone"
									value={formData.timezone}
									onChange={(e) =>
										setFormData({ ...formData, timezone: e.target.value })
									}
									className={INPUT_CLASS}
								/>
							</div>
						</div>

						<div className="grid grid-cols-2 gap-4">
							{NUMBER_FIELDS.map((field) => (
								<div key={field.key}>
									<label
										htmlFor={`tt-${field.key}`}
										className="block text-sm font-medium text-gray-700 mb-1"
									>
										{field.label} ({field.unit})
									</label>
									<input
										type="number"
										id={`tt-${field.key}`}
										value={formData[field.key]}
										onChange={(e) => setNumber(field.key, e.target.value)}
										min="0"
										step={field.step}
										className={INPUT_CLASS}
									/>
								</div>
							))}
						</div>

						<div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
							<button
								type="button"
								onClick={handleCancel}
								disabled={isSaving}
								className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
							>
								Cancel
							</button>
							<button
								type="submit"
								disabled={isSaving}
								className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
							>
								{isSaving ? "Saving..." : "Save Settings"}
							</button>
						</div>
					</form>
				) : settings ? (
					<dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
						<div>
							<dt className="text-gray-500">Country</dt>
							<dd className="text-gray-900 font-medium">
								{COUNTRY_OPTIONS.find((c) => c.code === settings.country_code)
									?.name || settings.country_code}
							</dd>
						</div>
						<div>
							<dt className="text-gray-500">Timezone</dt>
							<dd className="text-gray-900 font-medium">{settings.timezone}</dd>
						</div>
						{NUMBER_FIELDS.map((field) => (
							<div key={field.key}>
								<dt className="text-gray-500">{field.label}</dt>
								<dd className="text-gray-900 font-medium">
									{settings[field.key]} {field.unit}
								</dd>
							</div>
						))}
					</dl>
				) : (
					<p className="text-sm text-gray-500">
						No time tracking settings configured for this company.{" "}
						<button
							type="button"
							onClick={() => setIsEditing(true)}
							className="text-blue-600 hover:text-blue-800"
						>
							Configure now
						</button>
					</p>
				)}
			</div>
		</div>
	);
}
