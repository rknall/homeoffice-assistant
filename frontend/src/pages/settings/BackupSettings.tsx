// SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
// SPDX-License-Identifier: GPL-2.0-only
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, downloadBackup, performRestore, uploadBackupForValidation } from '@/api/client'
import { formatBytes } from '@/components/settings/formatBytes'
import { RestoreConfirmModal } from '@/components/settings/RestoreConfirmModal'
import { RestoreResultAlert } from '@/components/settings/RestoreResultAlert'
import { RestoreValidationAlert } from '@/components/settings/RestoreValidationAlert'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { useBreadcrumb } from '@/stores/breadcrumb'
import type { BackupInfo, RestoreResponse, RestoreValidationResponse } from '@/types'

export function BackupSettings() {
  const { setItems: setBreadcrumb } = useBreadcrumb()
  const [backupInfo, setBackupInfo] = useState<BackupInfo | null>(null)
  const [isLoadingInfo, setIsLoadingInfo] = useState(true)
  const [isCreatingBackup, setIsCreatingBackup] = useState(false)
  const [backupError, setBackupError] = useState<string | null>(null)
  const [backupSuccess, setBackupSuccess] = useState(false)

  // Create backup password state
  const [backupPassword, setBackupPassword] = useState('')
  const [backupPasswordConfirm, setBackupPasswordConfirm] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)

  // Restore state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<RestoreValidationResponse | null>(null)
  const [isRestoring, setIsRestoring] = useState(false)
  const [restoreResult, setRestoreResult] = useState<RestoreResponse | null>(null)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Restore password state
  const [restorePassword, setRestorePassword] = useState('')
  const [needsPassword, setNeedsPassword] = useState(false)

  useEffect(() => {
    setBreadcrumb([{ label: 'Settings', href: '/settings' }, { label: 'Backup' }])
  }, [setBreadcrumb])

  const fetchBackupInfo = useCallback(async () => {
    try {
      const info = await api.get<BackupInfo>('/backup/info')
      setBackupInfo(info)
    } catch (e) {
      setBackupError(e instanceof Error ? e.message : 'Failed to load backup info')
    } finally {
      setIsLoadingInfo(false)
    }
  }, [])

  useEffect(() => {
    fetchBackupInfo()
  }, [fetchBackupInfo])

  const validateBackupPassword = (): boolean => {
    if (backupPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return false
    }
    if (backupPassword !== backupPasswordConfirm) {
      setPasswordError('Passwords do not match')
      return false
    }
    setPasswordError(null)
    return true
  }

  const handleCreateBackup = async () => {
    if (!validateBackupPassword()) {
      return
    }

    setIsCreatingBackup(true)
    setBackupError(null)
    setBackupSuccess(false)
    try {
      await downloadBackup(backupPassword)
      setBackupSuccess(true)
      setBackupPassword('')
      setBackupPasswordConfirm('')
    } catch (e) {
      setBackupError(e instanceof Error ? e.message : 'Failed to create backup')
    } finally {
      setIsCreatingBackup(false)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setValidationResult(null)
      setRestoreResult(null)
      setRestorePassword('')
      setNeedsPassword(false)
    }
  }

  const handleValidate = async () => {
    if (!selectedFile) return
    setIsValidating(true)
    setValidationResult(null)
    try {
      const result = await uploadBackupForValidation(selectedFile, restorePassword || undefined)
      setValidationResult(result)

      // Check if password is needed
      if (!result.valid && result.metadata?.is_password_protected && !restorePassword) {
        setNeedsPassword(true)
      } else {
        setNeedsPassword(false)
      }
    } catch (e) {
      setValidationResult({
        valid: false,
        message: e instanceof Error ? e.message : 'Validation failed',
        metadata: null,
        warnings: [],
      })
    } finally {
      setIsValidating(false)
    }
  }

  const handleRestore = async () => {
    if (!selectedFile) return
    setShowConfirmModal(false)
    setIsRestoring(true)
    try {
      const result = await performRestore(selectedFile, restorePassword || undefined)
      setRestoreResult(result)
    } catch (e) {
      setRestoreResult({
        success: false,
        message: e instanceof Error ? e.message : 'Restore failed',
        requires_restart: false,
        migrations_run: false,
        migrations_message: '',
        configs_imported: 0,
      })
    } finally {
      setIsRestoring(false)
    }
  }

  const resetRestore = () => {
    setSelectedFile(null)
    setValidationResult(null)
    setRestoreResult(null)
    setRestorePassword('')
    setNeedsPassword(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Backup & Restore</h1>

      {/* Create Backup Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Create Backup</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingInfo ? (
            <div className="flex justify-center py-4">
              <Spinner />
            </div>
          ) : (
            <>
              {backupError && (
                <Alert variant="error" className="mb-4">
                  {backupError}
                </Alert>
              )}
              {backupSuccess && (
                <Alert variant="success" className="mb-4">
                  Backup created and downloaded successfully.
                </Alert>
              )}

              {backupInfo && (
                <div className="mb-4 space-y-2 text-sm text-gray-600">
                  <p>
                    Database:{' '}
                    {backupInfo.database_exists
                      ? formatBytes(backupInfo.database_size_bytes)
                      : 'Not found'}
                  </p>
                  <p>Avatars: {backupInfo.avatar_count} file(s)</p>
                </div>
              )}

              <div className="space-y-4 mb-4">
                <p className="text-sm text-gray-600">
                  Backups are encrypted with a password. You will need this password to restore the
                  backup later.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    type="password"
                    label="Backup Password"
                    placeholder="Enter password (min 8 characters)"
                    value={backupPassword}
                    onChange={(e) => setBackupPassword(e.target.value)}
                    error={
                      passwordError && backupPassword.length > 0 && backupPassword.length < 8
                        ? 'Password must be at least 8 characters'
                        : undefined
                    }
                  />
                  <Input
                    type="password"
                    label="Confirm Password"
                    placeholder="Confirm password"
                    value={backupPasswordConfirm}
                    onChange={(e) => setBackupPasswordConfirm(e.target.value)}
                    error={
                      passwordError &&
                      backupPasswordConfirm.length > 0 &&
                      backupPassword !== backupPasswordConfirm
                        ? 'Passwords do not match'
                        : undefined
                    }
                  />
                </div>
                {passwordError && <p className="text-sm text-red-600">{passwordError}</p>}
              </div>

              <Button
                onClick={handleCreateBackup}
                isLoading={isCreatingBackup}
                disabled={backupPassword.length < 8 || backupPassword !== backupPasswordConfirm}
              >
                Create Backup
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Restore Section */}
      <Card>
        <CardHeader>
          <CardTitle>Restore from Backup</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="warning" className="mb-4">
            Restoring a backup will replace all current data. A pre-restore backup will be created
            automatically. Your current admin account will be preserved.
          </Alert>

          {restoreResult && <RestoreResultAlert result={restoreResult} />}

          {!restoreResult?.success && (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="backup-file"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Select backup file (.tar.gz or .tar.gz.enc)
                </label>
                <input
                  id="backup-file"
                  ref={fileInputRef}
                  type="file"
                  accept=".gz,.tar.gz,.tgz,.enc,application/gzip,application/x-gzip,application/x-compressed-tar,application/octet-stream"
                  onChange={handleFileSelect}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-md file:border-0
                    file:text-sm file:font-medium
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100"
                />
              </div>
              {selectedFile && (
                <div className="text-sm text-gray-600">
                  Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})
                </div>
              )}
              {/* Password field for encrypted backups */}
              {(needsPassword || selectedFile?.name.endsWith('.enc')) && (
                <div>
                  <Input
                    type="password"
                    label="Backup Password"
                    placeholder="Enter the password used to create this backup"
                    value={restorePassword}
                    onChange={(e) => setRestorePassword(e.target.value)}
                  />
                  {needsPassword && !restorePassword && (
                    <p className="mt-1 text-sm text-amber-600">
                      This backup is password-protected. Please enter the password.
                    </p>
                  )}
                </div>
              )}
              {validationResult && <RestoreValidationAlert result={validationResult} />}
              <div className="flex gap-3">
                <Button
                  onClick={handleValidate}
                  disabled={!selectedFile}
                  isLoading={isValidating}
                  variant="secondary"
                >
                  Validate Backup
                </Button>
                <Button
                  onClick={() => setShowConfirmModal(true)}
                  disabled={!validationResult?.valid}
                  isLoading={isRestoring}
                  variant="danger"
                >
                  Restore Backup
                </Button>
                {selectedFile && (
                  <Button onClick={resetRestore} variant="ghost">
                    Clear
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <RestoreConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleRestore}
      />
    </div>
  )
}
