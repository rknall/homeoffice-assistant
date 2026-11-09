// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '@/api/client'
import { EventFormModal } from '@/components/EventFormModal'
import { AddExpenseModal } from '@/components/events/detail/AddExpenseModal'
import { DocumentExpenseModal } from '@/components/events/detail/DocumentExpenseModal'
import { DocumentReferenceModal } from '@/components/events/detail/DocumentReferenceModal'
import { DocumentsTab } from '@/components/events/detail/DocumentsTab'
import { EditExpenseModal } from '@/components/events/detail/EditExpenseModal'
import { EmailReportModal } from '@/components/events/detail/EmailReportModal'
import { EventCoverBanner } from '@/components/events/detail/EventCoverBanner'
import { EventStandardHeader } from '@/components/events/detail/EventStandardHeader'
import { EventSummaryCards } from '@/components/events/detail/EventSummaryCards'
import { ExpensesTab } from '@/components/events/detail/ExpensesTab'
import { PhotosTab } from '@/components/events/detail/PhotosTab'
import { useEmailReport } from '@/components/events/detail/useEmailReport'
import { useEventDetail } from '@/components/events/detail/useEventDetail'
import { useExpenseSelection } from '@/components/events/detail/useExpenseSelection'
import { GenerateReportModal } from '@/components/GenerateReportModal'
import { RejectionReasonModal } from '@/components/RejectionReasonModal'
import { SubmissionHistory } from '@/components/SubmissionHistory'
import { TodoList } from '@/components/TodoList'
import { Alert } from '@/components/ui/Alert'
import { Spinner } from '@/components/ui/Spinner'
import { Tab, TabList, TabPanel, Tabs } from '@/components/ui/Tabs'
import { useCompanies } from '@/stores/companies'
import { confirmAction } from '@/stores/confirm'
import type { Document, DocumentReference, Expense, Uuid } from '@/types'

export function EventDetail() {
  const { id } = useParams<{ id: Uuid }>()
  const navigate = useNavigate()
  const companies = useCompanies((s) => s.companies)
  const {
    event,
    expenses,
    preview,
    customFieldChoices,
    hasLlmIntegration,
    isLoading,
    error,
    setError,
    fetchData,
    documents,
    cover,
  } = useEventDetail(id)
  const selection = useExpenseSelection(id, expenses, fetchData, setError)
  const email = useEmailReport(id, event, selection.reportExpenseIds)
  const [photoCount, setPhotoCount] = useState(0)
  const [todoIncompleteCount, setTodoIncompleteCount] = useState(0)
  const [isEventEditModalOpen, setIsEventEditModalOpen] = useState(false)
  const [isAddExpenseOpen, setIsAddExpenseOpen] = useState(false)
  const [isReportModalOpen, setIsReportModalOpen] = useState(false)
  const [isRejectionModalOpen, setIsRejectionModalOpen] = useState(false)
  const [documentForExpense, setDocumentForExpense] = useState<Document | null>(null)
  const [expenseToEdit, setExpenseToEdit] = useState<Expense | null>(null)
  const [docRefToEdit, setDocRefToEdit] = useState<DocumentReference | null>(null)

  const deleteEvent = async () => {
    if (
      !id ||
      !(await confirmAction({
        title: 'Delete event',
        message:
          'Are you sure you want to delete this event? This will also delete all associated expenses, contacts, notes, and todos.',
        confirmLabel: 'Delete',
      }))
    ) {
      return
    }
    try {
      await api.delete(`/events/${id}`)
      navigate('/events')
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete event'))
    }
  }

  const deleteExpense = async (expenseId: string) => {
    if (
      !id ||
      !(await confirmAction({
        title: 'Delete expense',
        message: 'Are you sure you want to delete this expense?',
        confirmLabel: 'Delete',
      }))
    )
      return
    try {
      await api.delete(`/events/${id}/expenses/${expenseId}`)
      await fetchData()
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete expense'))
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!event || !id) {
    return (
      <div className="p-6">
        <Alert variant="error">Event not found</Alert>
      </div>
    )
  }

  const openEditModal = () => setIsEventEditModalOpen(true)

  return (
    <div>
      {cover.locationImage ? (
        <EventCoverBanner
          event={event}
          image={cover.locationImage}
          cover={cover}
          onEdit={openEditModal}
          onDelete={deleteEvent}
        />
      ) : (
        <EventStandardHeader event={event} onEdit={openEditModal} onDelete={deleteEvent} />
      )}

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      <EventSummaryCards preview={preview} />

      <Tabs defaultTab="expenses" className="mb-6">
        <TabList className="rounded-t-lg">
          <Tab value="expenses">Expenses</Tab>
          <Tab value="submissions">Submissions</Tab>
          <Tab value="documents">Documents</Tab>
          <Tab value="photos">Photos</Tab>
          <Tab value="todos" badge={todoIncompleteCount || undefined}>
            Todos
          </Tab>
        </TabList>

        <TabPanel value="expenses" className="bg-white rounded-b-lg shadow p-6">
          <ExpensesTab
            expenses={expenses}
            selection={selection}
            baseCurrency={preview?.currency}
            onExport={() => setIsReportModalOpen(true)}
            onEmail={email.open}
            onAdd={() => setIsAddExpenseOpen(true)}
            onReject={() => setIsRejectionModalOpen(true)}
            onEdit={setExpenseToEdit}
            onDelete={deleteExpense}
          />
        </TabPanel>

        <TabPanel value="submissions" className="bg-white rounded-b-lg shadow p-6">
          <SubmissionHistory eventId={id} />
        </TabPanel>

        <TabPanel value="documents" className="bg-white rounded-b-lg shadow p-6">
          <DocumentsTab
            eventId={id}
            documents={documents}
            onEditReference={setDocRefToEdit}
            onCreateExpense={setDocumentForExpense}
          />
        </TabPanel>

        <TabPanel value="photos" className="bg-white rounded-b-lg shadow p-6">
          <PhotosTab
            event={event}
            eventId={id}
            photoCount={photoCount}
            onPhotoCountChange={setPhotoCount}
          />
        </TabPanel>

        <TabPanel value="todos" className="bg-white rounded-b-lg shadow p-6">
          <TodoList
            eventId={id}
            event={event}
            onTodoCountChange={(_, incomplete) => setTodoIncompleteCount(incomplete)}
          />
        </TabPanel>
      </Tabs>

      <AddExpenseModal
        isOpen={isAddExpenseOpen}
        onClose={() => setIsAddExpenseOpen(false)}
        eventId={id}
        onSaved={fetchData}
        onError={setError}
      />

      <EventFormModal
        isOpen={isEventEditModalOpen}
        onClose={() => setIsEventEditModalOpen(false)}
        onSuccess={() => {
          void fetchData()
          setIsEventEditModalOpen(false)
        }}
        event={event}
        companies={companies}
        customFieldChoices={customFieldChoices}
      />

      <EmailReportModal email={email} />

      <DocumentExpenseModal
        document={documentForExpense}
        onClose={() => setDocumentForExpense(null)}
        eventId={id}
        hasLlmIntegration={hasLlmIntegration}
        onSaved={fetchData}
        onError={setError}
      />

      <EditExpenseModal
        expense={expenseToEdit}
        onClose={() => setExpenseToEdit(null)}
        eventId={id}
        hasLlmIntegration={hasLlmIntegration}
        onSaved={fetchData}
        onError={setError}
      />

      <GenerateReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        eventId={id}
        eventName={event.name || ''}
        expenses={expenses}
        baseCurrency={preview?.currency || 'EUR'}
        preselectedIds={selection.selectedExpenses}
        onReportGenerated={() => void fetchData()}
      />

      <RejectionReasonModal
        isOpen={isRejectionModalOpen}
        onClose={() => setIsRejectionModalOpen(false)}
        onConfirm={(reason) => {
          setIsRejectionModalOpen(false)
          selection.updateBulkStatus('rejected', reason)
        }}
        expenseCount={selection.selectedExpenses.size}
        isLoading={selection.isUpdatingBulkStatus}
      />

      <DocumentReferenceModal
        reference={docRefToEdit}
        onClose={() => setDocRefToEdit(null)}
        eventId={id}
        onSaved={documents.fetchDocumentReferences}
        onError={setError}
      />
    </div>
  )
}
