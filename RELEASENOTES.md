# Release Notes

## Version 0.2.0 (In Development)

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
