# Company Contacts & Email Template Enhancement

## Overview

This document outlines the implementation plan for extending the company and email template system to support multiple contacts per company with a tagging system, and linking email templates to specific contact types.

## Current State

### Company Model (`src/models/company.py`)
- **Fields**: name, type (employer/third_party), paperless_storage_path_id
- **Contact Info**: expense_recipient_email, expense_recipient_name, report_recipients (JSON text)
- **Limitation**: Single contact per company, limited to expense reports

### Contact Model (`src/models/contact.py`)
- **Purpose**: Event contacts (people met during events)
- **Not used for**: Company organizational contacts

### Email Template Model (`src/models/email_template.py`)
- **Fields**: name, reason, company_id, subject, body_html, body_text, is_default
- **Limitation**: No way to specify which contacts the template applies to

### Report Sending (`src/api/v1/reports.py`)
- Currently sends to `company.expense_recipient_email`
- Can override with custom recipient
- No concept of contact types or multiple recipients by role

## Requirements

1. **Enhanced Company Information**
   - General info: webpage, address, country, logo
   - Support for multiple contacts per company

2. **Contact Management**
   - Each contact can have multiple tags (Billing, HR, Technical, Support, Office, etc.)
   - One main/default contact per company
   - Multiple contacts can share the same tag

3. **Email Template Integration**
   - Templates specify which contact types they apply to
   - Display contact types in template list and details
   - Validate that required contact types exist
   - Auto-preselect contacts when sending based on template type

## Implementation Plan

### Phase 1: Database Schema

#### 1.1 Create ContactType Enum
**File**: `src/models/enums.py`

```python
class ContactType(str, Enum):
    """Contact type enumeration for company contacts."""

    BILLING = "billing"
    HR = "hr"
    TECHNICAL = "technical"
    SUPPORT = "support"
    OFFICE = "office"
    SALES = "sales"
    MANAGEMENT = "management"
    OTHER = "other"
```

#### 1.2 Create CompanyContact Model
**File**: `src/models/company_contact.py`

```python
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyContact(Base, TimestampMixin):
    """Contact associated with a company.

    Different from event contacts - these are organizational contacts
    that can receive reports, invoices, etc.
    """

    __tablename__ = "company_contacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    company_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contact information
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Contact types as JSON array of strings
    contact_types: Mapped[str] = mapped_column(
        Text,  # JSON array: ["billing", "hr"]
        nullable=False,
        default="[]",
    )

    # Main contact flag
    is_main_contact: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="contacts",
    )
```

#### 1.3 Update Company Model
**File**: `src/models/company.py`

Add new fields:
```python
# New general information fields
webpage: Mapped[str | None] = mapped_column(String(500), nullable=True)
address: Mapped[str | None] = mapped_column(Text, nullable=True)
country: Mapped[str | None] = mapped_column(String(100), nullable=True)
logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

# Deprecated fields (keep for migration, remove after)
# expense_recipient_email: Mapped[str | None] = ...
# expense_recipient_name: Mapped[str | None] = ...
# report_recipients: Mapped[str | None] = ...

# New relationship
contacts: Mapped[list["CompanyContact"]] = relationship(
    "CompanyContact",
    back_populates="company",
    cascade="all, delete-orphan",
)
```

#### 1.4 Update EmailTemplate Model
**File**: `src/models/email_template.py`

Add new field:
```python
# Contact types this template is applicable for
# Stored as JSON array: ["billing", "hr"]
contact_types: Mapped[str] = mapped_column(
    Text,  # JSON array
    nullable=False,
    default="[]",
)
```

#### 1.5 Create Migration
**File**: `alembic/versions/XXXX_add_company_contacts.py`

Migration steps:
1. Create `company_contacts` table
2. Add new fields to `companies` table (webpage, address, country, logo_url)
3. Add `contact_types` field to `email_templates` table
4. **Data Migration**: For each company with `expense_recipient_email`:
   - Create a CompanyContact with:
     - name = expense_recipient_name or company.name
     - email = expense_recipient_email
     - contact_types = ["billing"]
     - is_main_contact = True
5. For each existing "expense_report" template:
   - Set contact_types = ["billing"]
6. **Deprecation notice**: Mark old fields as deprecated (or remove after verifying migration)

### Phase 2: API Schemas

#### 2.1 Create CompanyContact Schemas
**File**: `src/schemas/company_contact.py`

```python
import datetime
from pydantic import BaseModel, EmailStr, Field

from src.models.enums import ContactType


class CompanyContactBase(BaseModel):
    """Base company contact schema."""

    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=200)
    department: str | None = Field(None, max_length=200)
    notes: str | None = None
    contact_types: list[ContactType] = Field(default_factory=list)
    is_main_contact: bool = False


class CompanyContactCreate(CompanyContactBase):
    """Schema for creating a company contact."""
    pass


class CompanyContactUpdate(BaseModel):
    """Schema for updating a company contact."""

    name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    title: str | None = Field(None, max_length=200)
    department: str | None = Field(None, max_length=200)
    notes: str | None = None
    contact_types: list[ContactType] | None = None
    is_main_contact: bool | None = None


class CompanyContactResponse(BaseModel):
    """Schema for company contact response."""

    id: str
    company_id: str
    name: str
    email: str
    phone: str | None
    title: str | None
    department: str | None
    notes: str | None
    contact_types: list[ContactType]
    is_main_contact: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
```

#### 2.2 Update Company Schemas
**File**: `src/schemas/company.py`

```python
# Add to CompanyCreate and CompanyUpdate
webpage: str | None = Field(None, max_length=500)
address: str | None = None
country: str | None = Field(None, max_length=100)
logo_url: str | None = Field(None, max_length=500)

# Add to CompanyResponse
webpage: str | None
address: str | None
country: str | None
logo_url: str | None
contacts: list[CompanyContactResponse] = []  # Include contacts in response
```

#### 2.3 Update EmailTemplate Schemas
**File**: `src/schemas/email_template.py`

```python
from src.models.enums import ContactType

# Add to EmailTemplateBase, Create, Update
contact_types: list[ContactType] = Field(default_factory=list)

# Add to EmailTemplateResponse
contact_types: list[ContactType]

# New validation schema
class TemplateContactValidation(BaseModel):
    """Validation result for template contacts."""

    is_valid: bool
    missing_types: list[ContactType]
    available_contacts: list[CompanyContactResponse]
    message: str
```

#### 2.4 Update SendReportRequest
**File**: `src/api/v1/reports.py`

```python
class SendReportRequest(BaseModel):
    """Schema for sending expense report via email."""

    recipient_emails: list[str] | None = Field(
        None,
        description="Email addresses to send report to. If not provided, uses contacts based on template type.",
    )
    template_id: str | None = Field(
        None,
        description="Email template ID to use. If not provided, uses default template.",
    )
    # Add flag to auto-select contacts
    auto_select_contacts: bool = Field(
        True,
        description="Automatically select contacts based on template contact types.",
    )
```

### Phase 3: Services

#### 3.1 Create CompanyContact Service
**File**: `src/services/company_contact_service.py`

Functions:
- `get_contacts(db, company_id)` - Get all contacts for a company
- `get_contact(db, contact_id)` - Get a single contact
- `create_contact(db, company_id, data)` - Create a new contact
- `update_contact(db, contact, data)` - Update existing contact
- `delete_contact(db, contact)` - Delete a contact
- `get_main_contact(db, company_id)` - Get the main contact
- `set_main_contact(db, contact_id)` - Set a contact as main (unset others)
- `get_contacts_by_type(db, company_id, contact_types)` - Get contacts matching any of the specified types
- `validate_contact_types_exist(db, company_id, required_types)` - Check if company has contacts for all required types

#### 3.2 Update EmailTemplate Service
**File**: `src/services/email_template_service.py`

Add functions:
- `validate_template_contacts(db, template, company_id)` - Check if company has required contact types
- Update `build_expense_report_context()` to include contact information in context
- Add template variable for contact info: `{{contact.name}}`, `{{contact.email}}`

#### 3.3 Update Report Service
**File**: `src/api/v1/reports.py`

Update `send_expense_report()`:
1. If `auto_select_contacts` is True and no `recipient_emails` provided:
   - Get template contact_types
   - Query contacts matching those types
   - Use main contact as fallback
2. If template has contact_types but no matching contacts exist:
   - Return error with details about missing types
3. Support sending to multiple recipients

### Phase 4: API Endpoints

#### 4.1 Company Contact Endpoints
**File**: `src/api/v1/company_contacts.py` (new)

```python
router = APIRouter()

@router.get("/companies/{company_id}/contacts")
async def list_contacts(company_id: str, db: Session = Depends(get_db))
    """List all contacts for a company."""

@router.get("/companies/{company_id}/contacts/{contact_id}")
async def get_contact(company_id: str, contact_id: str, db: Session = Depends(get_db))
    """Get a specific contact."""

@router.post("/companies/{company_id}/contacts")
async def create_contact(company_id: str, data: CompanyContactCreate, db: Session = Depends(get_db))
    """Create a new contact for a company."""

@router.put("/companies/{company_id}/contacts/{contact_id}")
async def update_contact(company_id: str, contact_id: str, data: CompanyContactUpdate, db: Session = Depends(get_db))
    """Update a contact."""

@router.delete("/companies/{company_id}/contacts/{contact_id}")
async def delete_contact(company_id: str, contact_id: str, db: Session = Depends(get_db))
    """Delete a contact."""

@router.post("/companies/{company_id}/contacts/{contact_id}/set-main")
async def set_main_contact(company_id: str, contact_id: str, db: Session = Depends(get_db))
    """Set a contact as the main contact."""

@router.get("/companies/{company_id}/contacts/by-type/{contact_type}")
async def get_contacts_by_type(company_id: str, contact_type: ContactType, db: Session = Depends(get_db))
    """Get contacts by type."""
```

#### 4.2 Update Company Endpoints
**File**: `src/api/v1/companies.py`

- Update response to include contacts
- Add filters/options to include/exclude contacts

#### 4.3 Add Template Validation Endpoint
**File**: `src/api/v1/email_templates.py`

```python
@router.get("/email-templates/{template_id}/validate-contacts/{company_id}")
async def validate_template_contacts(template_id: str, company_id: str, db: Session = Depends(get_db))
    """Validate that a company has the required contact types for a template."""
```

### Phase 5: Frontend

#### 5.1 Create Contact Type Constants
**File**: `frontend/src/types/contactTypes.ts`

```typescript
export enum ContactType {
  BILLING = 'billing',
  HR = 'hr',
  TECHNICAL = 'technical',
  SUPPORT = 'support',
  OFFICE = 'office',
  SALES = 'sales',
  MANAGEMENT = 'management',
  OTHER = 'other',
}

export const CONTACT_TYPE_LABELS: Record<ContactType, string> = {
  [ContactType.BILLING]: 'Billing',
  [ContactType.HR]: 'HR',
  [ContactType.TECHNICAL]: 'Technical',
  [ContactType.SUPPORT]: 'Support',
  [ContactType.OFFICE]: 'Office',
  [ContactType.SALES]: 'Sales',
  [ContactType.MANAGEMENT]: 'Management',
  [ContactType.OTHER]: 'Other',
};
```

#### 5.2 Create CompanyContact Components
**Files**:
- `frontend/src/components/CompanyContactList.tsx` - List contacts with tags
- `frontend/src/components/CompanyContactForm.tsx` - Create/edit contact form
- `frontend/src/components/CompanyContactCard.tsx` - Display single contact
- `frontend/src/components/ContactTypeSelector.tsx` - Multi-select for contact types

#### 5.3 Update Company Form
**File**: `frontend/src/pages/Companies.tsx` or similar

Add fields:
- Webpage (URL input)
- Address (textarea)
- Country (select or text input)
- Logo (file upload or URL)

Add section for managing contacts:
- List existing contacts
- Add/edit/delete contacts
- Mark main contact

#### 5.4 Update Email Template Components

**File**: `frontend/src/components/EmailTemplateEditor.tsx`

Add:
- Contact type selector (multi-select)
- Display selected contact types as badges
- Show warning if no contact types selected

**File**: `frontend/src/pages/settings/EmailTemplateSettings.tsx`

Update template list to show:
- Contact types as badges/tags
- Warning icon if template has contact_types but company has no matching contacts

**File**: `frontend/src/components/EmailTemplateSelector.tsx`

When selecting template for sending:
- Show contact types required by template
- Display validation result (missing contact types)
- Show which contacts will receive the email
- Allow manual override of recipients

#### 5.5 Update Send Report Dialog
**Component**: Wherever expense reports are sent

Add:
- Display auto-selected contacts based on template
- Allow adding/removing recipients
- Show contact tags for each recipient
- Validate before sending

### Phase 6: Testing

#### 6.1 Backend Tests

**Unit Tests** (`tests/unit/test_services/test_company_contact_service.py`):
- Contact CRUD operations
- Main contact logic (only one per company)
- Contact type filtering
- Validation logic

**Unit Tests** (`tests/unit/test_services/test_email_template_service.py`):
- Template validation with contact types
- Context building with contact info

**Integration Tests** (`tests/integration/test_api/test_company_contacts.py`):
- All company contact endpoints
- Permission checks
- Validation errors

**Integration Tests** (`tests/integration/test_api/test_reports.py`):
- Update report sending tests
- Auto-selection of contacts
- Multiple recipients
- Error cases (missing contacts)

#### 6.2 Frontend Tests
- Component rendering
- Form validation
- Contact selection logic
- Error states

### Phase 7: Documentation & Migration

#### 7.1 Update RELEASENOTES.md

Add entry:
```markdown
### v0.3.0 (In Development)

#### Major Features

##### Enhanced Company Contact Management
- Companies can now store multiple contacts with role-based tagging
- Added general company information: webpage, address, country, logo
- Each company can designate one main contact
- Contact tags include: Billing, HR, Technical, Support, Office, Sales, Management
- Multiple contacts can share the same tag

##### Email Template Contact Integration
- Email templates now specify which contact types they apply to
- When sending reports, contacts are automatically selected based on template type
- Templates display validation warnings if required contact types are missing
- Support for sending to multiple recipients simultaneously

##### Improved Report Sending
- Automatic recipient selection based on email template configuration
- Manual override option for recipient selection
- Better error messages when contacts are not configured
- Support for multiple recipients per report

#### Data Migration Notes
- Existing company expense recipients automatically migrated to contacts with "Billing" tag
- All existing expense report templates tagged with "Billing" contact type
- Old company contact fields deprecated (data preserved during transition)
```

#### 7.2 Update CLAUDE.md

Add section about the new contact system:
```markdown
## Company Contact System

### Contact Types
Companies can have multiple contacts, each tagged with one or more types:
- Billing: For invoices and expense reports
- HR: For personnel-related correspondence
- Technical: For technical support and questions
- Support: For general support inquiries
- Office: For office/location contacts
- Sales: For sales-related communication
- Management: For management-level contacts
- Other: Catch-all category

### Email Template Integration
Templates specify which contact types they're applicable for. When sending emails:
1. System auto-selects contacts matching template's contact_types
2. Falls back to main contact if no type matches
3. Validates that required contact types exist before sending
4. Allows manual override of recipients

### Database Structure
- `CompanyContact`: Separate from event contacts (people met during events)
- Stores contact_types as JSON array in database
- One main_contact per company (is_main_contact flag)
- Cascade delete with company
```

#### 7.3 API Documentation
- Update OpenAPI/Swagger docs
- Add examples for new endpoints
- Document contact type enum values

## Implementation Order

1. **Database & Models** (Phase 1)
   - Create enums, models, and migration
   - Test migration with sample data

2. **Backend Services** (Phase 3)
   - Implement contact service
   - Update email template service

3. **API Endpoints** (Phase 4)
   - Company contact CRUD
   - Template validation
   - Update report sending

4. **Backend Tests** (Phase 6.1)
   - Unit and integration tests

5. **Frontend Types & API Client** (Phase 5.1)
   - TypeScript interfaces
   - API client functions

6. **Frontend Components** (Phase 5.2-5.5)
   - Contact management UI
   - Company form updates
   - Email template updates
   - Send report dialog

7. **Frontend Tests** (Phase 6.2)

8. **Documentation** (Phase 7)

## Backward Compatibility

### Migration Strategy
1. Keep deprecated fields in Company model temporarily
2. Migrate existing data to new structure
3. Add validation to prevent null main contacts
4. Verify all existing functionality works with new system
5. Remove deprecated fields in future version

### Breaking Changes
- None (fully backward compatible)
- Old API fields deprecated but functional
- New fields optional during transition

## Future Enhancements

1. **Custom Contact Types**
   - Allow users to define their own contact types beyond predefined ones

2. **Contact Groups**
   - Group contacts for bulk operations

3. **Email Threading**
   - Track email conversations per contact

4. **Contact History**
   - Log all emails sent to each contact

5. **Template Permissions**
   - Restrict certain templates to specific user roles

## Questions to Resolve

1. **Logo Storage**: Should logos be:
   - URL only (external hosting)
   - Uploaded and stored locally
   - Both options?

2. **Country Field**: Should it be:
   - Free text
   - Dropdown with ISO codes
   - Autocomplete

3. **Multiple Recipients UI**: When template selects multiple contacts:
   - Send one email with all recipients
   - Send separate emails to each recipient
   - Let user choose per-send?

4. **Contact Validation**: Should we:
   - Block template creation if no contacts exist?
   - Show warning only?
   - Validate at send-time only?

5. **Main Contact Requirement**: Should every company:
   - Require exactly one main contact?
   - Allow zero (use first contact as fallback)?
   - Allow multiple main contacts?
