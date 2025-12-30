# Business Card Scanner

## Status
Idea - Not Started

## Plugin Candidate
Yes - This is a good plugin candidate. Core app doesn't need this functionality to work.

## Problem
After conferences, trade shows, or business meetings, users collect business cards. Manually entering contact information is tedious and error-prone. This naturally feeds into the Contacts system and Travel Reports.

## Proposed Solution

### Approach
Use Ollama vision models (same infrastructure as OCR for expenses) to extract structured contact data from business card photos.

### Data Flow
```
Photo Upload → Vision Model → Contact Draft → User Review → Save to Contacts
```

### Extracted Fields
- Name (first, last)
- Company
- Job title
- Email(s)
- Phone(s)
- Address
- Website
- LinkedIn/social handles

## Plugin Architecture

### Core App Provides
- Contact model and API
- Event association (which event did you meet this person?)
- Ollama integration config (shared with expense OCR)

### Plugin Provides
- "Scan Card" UI component
- Extraction prompt/logic
- Batch scanning support
- Duplicate detection

## Integration Points

| Integration | Purpose |
|-------------|---------|
| **Contacts** | Target for extracted data |
| **Events** | Associate contact with event where met |
| **Ollama** | Vision model for extraction |
| **Immich** | Optional: pull card photos from album |

## UI Concept

1. On Contact creation: "Scan from Business Card" button
2. Upload/capture photo
3. Show extracted fields with confidence indicators
4. User reviews, corrects, saves
5. Optional: link to event

## Example Prompt (Ollama Vision)

```
Extract contact information from this business card image as JSON:
- first_name, last_name
- company
- job_title
- emails (array)
- phones (array, with type: mobile/work/fax)
- address (street, city, postal_code, country)
- website
- linkedin_url

Return only valid JSON. Use null for fields not found.
```

## Considerations

- **Multiple cards**: Batch upload for post-conference processing
- **Languages**: Cards may be in various languages/scripts
- **Duplicates**: Warn if contact with same email/phone exists
- **Photo storage**: Keep original card image linked to contact?

## Related
- [Local OCR for Expenses](local-ocr-expense-recognition.md) - Shared Ollama infrastructure
- Contact management (core feature)
- Travel Report Generation - Contacts feed into reports
