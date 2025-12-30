# Company Documents

## Status
Idea - Not Started

## Plugin Candidate
No - This is a core feature. Documents are tightly coupled to Companies and affect expense/event workflows.

## Problem
Users work with multiple clients/employers and need to track important documents per company:
- Contracts and agreements
- NDAs
- Rate cards / pricing agreements
- Travel policies
- Expense reimbursement rules

Currently there's no way to attach these to a Company or get reminders when they expire.

## Proposed Solution

### Document Types
| Type | Has Expiry | Description |
|------|------------|-------------|
| Contract | Yes | Service agreements, employment contracts |
| NDA | Yes | Non-disclosure agreements |
| Policy | No | Travel policies, expense rules |
| Rate Card | Yes | Billing rates, per diem amounts |
| Other | Optional | Catch-all |

### Core Features
1. Upload documents to a Company
2. Set document type and optional expiry date
3. Expiry reminders (30 days, 7 days, expired)
4. Quick access from Company detail view
5. Reference in expense reports ("per contract dated...")

## Data Model

```python
class CompanyDocument(Base, TimestampMixin):
    id: UUID
    company_id: UUID  # FK to Company
    name: str  # "2024 Service Agreement"
    document_type: str  # contract, nda, policy, rate_card, other
    description: str | None
    expires_at: date | None
    reminder_days: int | None  # days before expiry to remind

    # Storage
    storage_type: str  # local, paperless, s3
    storage_reference: str  # file path or external ID

    # Metadata
    uploaded_by: UUID  # FK to User
    file_name: str
    file_size: int
    mime_type: str
```

## Storage Options

| Option | Implementation |
|--------|---------------|
| **Local** | Store in `data/documents/{company_id}/` |
| **Paperless** | Link to existing Paperless document by ID |
| **S3/WebDAV** | If file storage integration is implemented |

## UI Components

### Company Detail Page
- "Documents" tab/section
- List with type, name, expiry status
- Upload button
- Quick preview/download

### Document Upload Modal
- File picker
- Document type selector
- Name (auto-filled from filename)
- Expiry date (optional)
- Reminder toggle

### Dashboard Widget
- "Expiring Soon" list
- Documents expiring in next 30 days
- Click to view/renew

## API Endpoints

```
GET    /api/v1/companies/{id}/documents
POST   /api/v1/companies/{id}/documents
GET    /api/v1/companies/{id}/documents/{doc_id}
PUT    /api/v1/companies/{id}/documents/{doc_id}
DELETE /api/v1/companies/{id}/documents/{doc_id}
GET    /api/v1/companies/{id}/documents/{doc_id}/download

GET    /api/v1/documents/expiring?days=30  # Cross-company
```

## Expiry Notification Flow

1. Daily job checks for documents expiring within reminder window
2. Creates notification in app
3. Optional: Email notification (if SMTP configured)

## Considerations

- **Encryption**: Documents may contain sensitive data - encrypt at rest?
- **Versioning**: Keep old versions when re-uploading?
- **Search**: Full-text search within documents? (defer to Paperless)
- **Permissions**: Multi-user - who can see which company docs?

## Related
- Company management (parent feature)
- [File Storage Integrations](file-storage-integrations.md) - Alternative storage backends
- Expense reports - Reference contract terms
