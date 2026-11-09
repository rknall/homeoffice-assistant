// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only

import { ChevronRight, Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage, getCompanyLogoUrl } from '@/api/client'
import { CompanyFormModal } from '@/components/CompanyFormModal'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import { useCompanies } from '@/stores/companies'
import { confirmAction } from '@/stores/confirm'
import type { Company } from '@/types'
import { companyTypeLabels } from '@/utils/labels'

export function Companies() {
  const navigate = useNavigate()
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const { companies, isLoading, error: loadError, fetchCompanies } = useCompanies()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Company | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setBreadcrumb([{ label: 'Companies' }])
  }, [setBreadcrumb])

  useEffect(() => {
    fetchCompanies()
  }, [fetchCompanies])

  const deleteCompany = async (id: string) => {
    if (
      !(await confirmAction({
        title: 'Delete company',
        message: 'Are you sure you want to delete this company?',
        confirmLabel: 'Delete',
      }))
    )
      return
    try {
      await api.delete(`/companies/${id}`)
      await fetchCompanies()
    } catch (e) {
      setError(errorMessage(e, 'Failed to delete company'))
    }
  }

  const handleCompanyCreated = (company?: Company) => {
    if (company) {
      navigate(`/companies/${company.id}`)
    }
  }

  const handleCompanyUpdated = () => {
    fetchCompanies()
    setEditingCompany(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Company
        </Button>
      </div>

      {(error || loadError) && (
        <Alert variant="error" className="mb-4">
          {error || loadError}
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Companies</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : companies.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No companies yet. Add your first company to get started.
            </p>
          ) : (
            <div className="divide-y divide-gray-200">
              {companies.map((company) => (
                <div
                  key={company.id}
                  className="flex items-center justify-between hover:bg-gray-50 -mx-4 px-4 rounded"
                >
                  <button
                    type="button"
                    className="flex flex-1 items-center justify-between py-4 cursor-pointer text-left"
                    onClick={() => navigate(`/companies/${company.id}`)}
                  >
                    <div className="flex items-center gap-3">
                      {company.logo_path && (
                        <img
                          src={getCompanyLogoUrl(company.id)}
                          alt={`${company.name} logo`}
                          className="h-10 w-10 object-contain rounded border border-gray-200"
                        />
                      )}
                      <div>
                        <h3 className="font-medium text-gray-900">{company.name}</h3>
                        <p className="text-sm text-gray-500">
                          {company.contacts?.find((c) => c.is_main_contact)?.email ||
                            'No main contact'}
                        </p>
                      </div>
                    </div>
                    <Badge variant={company.type === 'employer' ? 'info' : 'default'}>
                      {companyTypeLabels[company.type]}
                    </Badge>
                  </button>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      type="button"
                      onClick={() => setEditingCompany(company)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Edit company"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteCompany(company.id)}
                      className="p-1 text-gray-400 hover:text-red-600"
                      title="Delete company"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <ChevronRight className="h-4 w-4 text-gray-400" aria-hidden="true" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Company Modal */}
      <CompanyFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleCompanyCreated}
      />

      {/* Edit Company Modal */}
      <CompanyFormModal
        isOpen={!!editingCompany}
        onClose={() => setEditingCompany(null)}
        onSuccess={handleCompanyUpdated}
        company={editingCompany}
      />
    </div>
  )
}
