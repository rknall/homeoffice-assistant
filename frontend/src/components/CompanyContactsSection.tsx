// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { Pencil, Plus, Star, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '@/api/client'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { confirmAction } from '@/stores/confirm'
import type { CompanyContact } from '@/types'
import { CompanyContactFormModal } from './CompanyContactFormModal'
import { ContactTypeBadge } from './ContactTypeBadge'

interface CompanyContactsSectionProps {
  companyId: string
  contacts: CompanyContact[]
  onContactsChanged: () => void
}

export function CompanyContactsSection({
  companyId,
  contacts,
  onContactsChanged,
}: CompanyContactsSectionProps) {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingContact, setEditingContact] = useState<CompanyContact | null>(null)
  const [error, setError] = useState<string | null>(null)

  const openModal = (contact?: CompanyContact) => {
    setEditingContact(contact || null)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingContact(null)
  }

  const handleContactSaved = () => {
    closeModal()
    onContactsChanged()
  }

  const deleteContact = async (contactId: string) => {
    if (
      !(await confirmAction({
        title: 'Delete contact',
        message: 'Are you sure you want to delete this contact?',
        confirmLabel: 'Delete',
      }))
    )
      return
    try {
      await api.delete(`/companies/${companyId}/contacts/${contactId}`)
      onContactsChanged()
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete contact'))
    }
  }

  const setMainContact = async (contactId: string) => {
    try {
      await api.post(`/companies/${companyId}/contacts/${contactId}/set-main`)
      onContactsChanged()
    } catch (e) {
      setError(errorMessage(e, 'Failed to set main contact'))
    }
  }

  // Sort contacts: main contact first, then by name
  const sortedContacts = [...contacts].sort((a, b) => {
    if (a.is_main_contact && !b.is_main_contact) return -1
    if (!a.is_main_contact && b.is_main_contact) return 1
    return a.name.localeCompare(b.name)
  })

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Contacts</CardTitle>
          <Button onClick={() => openModal()}>
            <Plus className="h-4 w-4 mr-2" />
            Add Contact
          </Button>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md mb-4">{error}</div>
          )}
          {sortedContacts.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No contacts configured for this company.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {sortedContacts.map((contact) => (
                <div key={contact.id} className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900 truncate">{contact.name}</h3>
                        {contact.is_main_contact && <Badge variant="info">Main Contact</Badge>}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{contact.email}</p>
                      {contact.phone && <p className="text-sm text-gray-500">{contact.phone}</p>}
                      {(contact.title || contact.department) && (
                        <p className="text-sm text-gray-500 mt-1">
                          {[contact.title, contact.department].filter(Boolean).join(' - ')}
                        </p>
                      )}
                      {contact.contact_types && contact.contact_types.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {contact.contact_types.map((type) => (
                            <ContactTypeBadge key={type} type={type} size="sm" />
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 ml-4">
                      {!contact.is_main_contact && (
                        <button
                          type="button"
                          onClick={() => setMainContact(contact.id)}
                          className="p-1 text-gray-400 hover:text-yellow-500"
                          title="Set as main contact"
                        >
                          <Star className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => openModal(contact)}
                        className="p-1 text-gray-400 hover:text-gray-600"
                        title="Edit contact"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteContact(contact.id)}
                        className="p-1 text-gray-400 hover:text-red-600"
                        title="Delete contact"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <CompanyContactFormModal
        isOpen={isModalOpen}
        onClose={closeModal}
        onSuccess={handleContactSaved}
        companyId={companyId}
        contact={editingContact}
      />
    </>
  )
}
