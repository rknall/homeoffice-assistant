# Release Notes

## Version 0.2.3

### Major Features

#### Company Contacts
- Multiple contacts per company with email, phone, title, department, and notes
- Contact type tagging system (Billing, HR, Technical, Support, Office, Sales, Management, Other)
- Main contact designation with automatic selection of first contact
- Contacts displayed in company detail view with type badges

#### Company Information Enhancements
- Company logo upload and display (PNG, JPG, GIF, SVG, WebP up to 5MB)
- New company fields: website URL, address, and country
- Country autocomplete with browser locale detection

#### Email Template Contact Types
- Link email templates to specific contact types (e.g., Billing)
- Auto-select recipients based on template contact types when sending reports
- Fallback to main contact if no matching types found
- Template validation shows which contact types are missing

### Improvements

#### Company Management
- Enhanced company form with logo upload, address fields, and country selection
- Removed legacy expense recipient fields (replaced by company contacts)
- Contacts section on company detail page

#### Report Sending
- Multiple recipients in single email
- Automatic recipient selection from contacts matching template types
- Clear validation messages when contacts are missing

### Bug Fixes

- Fixed backup service tests after project rename from Travel Manager to HomeOffice Assistant

---

## Version 0.2.0

### Major Features

#### Immich Integration
- Connect to Immich photo server for event photos
- Search photos by date range and location
- Select cover images for events from Immich library
- Photo thumbnails displayed in event views

#### Location Support
- Add location fields (city, country, coordinates) to events
- Location displayed on event cards and detail pages
- Map pin indicators in event listings

#### Cover Images
- Event cover images with gradient overlays
- Cover image backgrounds on event list and detail pages
- Dashboard displays event cover thumbnails
- Support for both Immich photos and Unsplash images

#### Unsplash Integration
- Search and select cover images from Unsplash
- Unsplash form fields for image selection
- Proper attribution for Unsplash images

### Improvements

#### User Registration
- Added display name (full name) field to registration
- Real-time password validation with requirement indicators
- Auto-generate username from first name
- Username availability check with automatic suffix if taken
- Enhanced email validation

#### Regional Settings
- "Detect from Browser" button to auto-detect locale settings
- Auto-detects date format, time format, and timezone
- Success notification when settings are saved

#### Event Management
- "New Event" button disabled until at least one company exists
- Tooltip explains company requirement
- Removed redundant "New Event" button from dashboard

#### Company Management
- Email validation with real-time error display on blur
- Unique email constraint prevents duplicate expense recipient emails

#### Shared Validation
- Reusable email validation utilities (`frontend/src/lib/validation.ts`)
- Consistent email validation across Company forms and SMTP integration settings

#### Email Templates
- Prevent deletion of last global template (backend + frontend)
- Prefill option when creating new templates with default content
- "Use Default" / "Start Empty" prompt for new templates

#### UI/UX Improvements
- Shared form modals for consistent editing experience
- Improved backup/restore functionality
- Better form styling and layout

### Bug Fixes

- Fix event location and cover image saving
- Fix Immich search for future events

### Warnings & Guidance

- SMTP configuration warning on Email Templates settings page when no email integration configured
- SMTP configuration warning on Company detail page with link to integration settings

---

## Version 0.1.1

### Features
- Backup and restore functionality
- Paperless integration improvements

### Bug Fixes
- Various Paperless integration fixes

---

## Version 0.1.0

Initial release with core functionality:
- Event management (CRUD operations)
- Company management with Paperless storage path selection
- Expense tracking and management
- Paperless-ngx integration for document management
- Expense report generation (Excel + ZIP)
- User authentication with session management
- SMTP email integration for sending reports
- Customizable email templates
- Regional date/time format settings
- Breadcrumb navigation
