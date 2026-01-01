// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useCallback, useEffect, useState } from 'react'
import {
  formatHours,
  getWeekEnd,
  getWeekStart,
  leaveBalanceApi,
  timeRecordsApi,
  toISODateString,
} from '../api'
import type {
  ComplianceWarning,
  LeaveBalance,
  TimeRecord,
  TimeRecordCreate,
  TimeRecordUpdate,
  TimeRecordWithWarnings,
} from '../types'
import { TimeRecordForm } from './TimeRecordForm'
import { WeekView } from './WeekView'

interface TimeTrackingPageProps {
  companyId: string
  companyName: string
}

export function TimeTrackingPage({ companyId, companyName }: TimeTrackingPageProps) {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [records, setRecords] = useState<TimeRecord[]>([])
  const [vacationBalance, setVacationBalance] = useState<LeaveBalance | null>(null)
  const [compTimeBalance, setCompTimeBalance] = useState<LeaveBalance | null>(null)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedRecord, setSelectedRecord] = useState<TimeRecord | null>(null)
  const [formWarnings, setFormWarnings] = useState<ComplianceWarning[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [todayRecord, setTodayRecord] = useState<TimeRecord | null>(null)

  const loadRecords = useCallback(async () => {
    setIsLoading(true)
    try {
      const weekStart = getWeekStart(currentDate)
      const weekEnd = getWeekEnd(currentDate)

      const response = await timeRecordsApi.list({
        company_id: companyId,
        start_date: toISODateString(weekStart),
        end_date: toISODateString(weekEnd),
      })
      setRecords(response.records)
    } catch (err) {
      console.error('Failed to load records:', err)
    } finally {
      setIsLoading(false)
    }
  }, [companyId, currentDate])

  const loadBalances = useCallback(async () => {
    try {
      const balances = await leaveBalanceApi.get(companyId)
      setVacationBalance(balances.vacation)
      setCompTimeBalance(balances.comp_time)
    } catch (err) {
      console.error('Failed to load balances:', err)
    }
  }, [companyId])

  const loadTodayRecord = useCallback(async () => {
    try {
      const record = await timeRecordsApi.getToday(companyId)
      setTodayRecord(record)
    } catch (err) {
      console.error('Failed to load today record:', err)
    }
  }, [companyId])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  useEffect(() => {
    loadBalances()
    loadTodayRecord()
  }, [loadBalances, loadTodayRecord])

  const handleCheckIn = useCallback(async () => {
    try {
      const result = await timeRecordsApi.checkIn(companyId)
      setTodayRecord(result.record)
      await loadRecords()
    } catch (err) {
      console.error('Check-in failed:', err)
    }
  }, [companyId, loadRecords])

  const handleCheckOut = useCallback(async () => {
    if (!todayRecord) return
    try {
      const result = await timeRecordsApi.checkOut(todayRecord.id)
      setTodayRecord(result.record)
      await loadRecords()
    } catch (err) {
      console.error('Check-out failed:', err)
    }
  }, [todayRecord, loadRecords])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + I for check-in
      if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
        e.preventDefault()
        handleCheckIn()
      }
      // Ctrl/Cmd + O for check-out
      if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
        e.preventDefault()
        handleCheckOut()
      }
      // Escape to close form
      if (e.key === 'Escape' && selectedDate) {
        setSelectedDate(null)
        setSelectedRecord(null)
        setFormWarnings([])
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedDate, handleCheckIn, handleCheckOut])

  const handleDayClick = (date: string, record?: TimeRecord) => {
    setSelectedDate(date)
    setSelectedRecord(record || null)
    setFormWarnings([])
  }

  const handleFormSubmit = async (data: TimeRecordCreate | TimeRecordUpdate) => {
    setIsSaving(true)
    try {
      let result: TimeRecordWithWarnings
      if (selectedRecord) {
        result = await timeRecordsApi.update(selectedRecord.id, data as TimeRecordUpdate)
      } else {
        result = await timeRecordsApi.create(data as TimeRecordCreate)
      }

      setFormWarnings(result.warnings)

      // If no errors, close the form
      if (!result.warnings.some((w) => w.level === 'error')) {
        setSelectedDate(null)
        setSelectedRecord(null)
        setFormWarnings([])
        await loadRecords()
        await loadBalances()
        await loadTodayRecord()
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleFormCancel = () => {
    setSelectedDate(null)
    setSelectedRecord(null)
    setFormWarnings([])
  }

  const canCheckIn = !todayRecord || !todayRecord.check_in
  const canCheckOut = todayRecord?.check_in && !todayRecord.check_out

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
            <h3 className="text-sm font-medium text-gray-500">Vacation Balance</h3>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {vacationBalance.available_days}
              </span>
              <span className="text-sm text-gray-500">days available</span>
            </div>
            <p className="mt-1 text-xs text-gray-400">
              {vacationBalance.used_days} used / {vacationBalance.entitled_days} entitled
              {vacationBalance.carried_over > 0 &&
                ` + ${vacationBalance.carried_over} carried over`}
            </p>
          </div>
        )}
        {compTimeBalance && (
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-sm font-medium text-gray-500">Comp Time Balance</h3>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">
                {formatHours(compTimeBalance.available_days * 8)}
              </span>
              <span className="text-sm text-gray-500">available</span>
            </div>
            <p className="mt-1 text-xs text-gray-400">
              {formatHours(compTimeBalance.entitled_days * 8)} accrued,{' '}
              {formatHours(compTimeBalance.used_days * 8)} used
            </p>
          </div>
        )}
      </div>

      {/* Week view */}
      <WeekView
        records={records}
        currentDate={currentDate}
        onDateChange={setCurrentDate}
        onDayClick={handleDayClick}
        isLoading={isLoading}
      />

      {/* Time record form modal */}
      {selectedDate && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            {/* Backdrop */}
            <button
              type="button"
              className="fixed inset-0 bg-black bg-opacity-25 cursor-default"
              onClick={handleFormCancel}
              onKeyDown={(e) => e.key === 'Escape' && handleFormCancel()}
              aria-label="Close modal"
            />

            {/* Modal */}
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                {selectedRecord ? 'Edit Time Record' : 'New Time Record'}
              </h2>
              <TimeRecordForm
                record={selectedRecord}
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
        Keyboard shortcuts: <kbd className="px-1 py-0.5 bg-gray-100 rounded">Ctrl+I</kbd> Check In,{' '}
        <kbd className="px-1 py-0.5 bg-gray-100 rounded">Ctrl+O</kbd> Check Out,{' '}
        <kbd className="px-1 py-0.5 bg-gray-100 rounded">Esc</kbd> Close form
      </div>
    </div>
  )
}
