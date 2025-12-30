# Recurring Events

## Status
Idea - Not Started

## Plugin Candidate
Maybe - Could go either way. Recurrence is useful but adds complexity. Start as core, extract to plugin if it bloats the codebase.

## Problem
Many business trips follow patterns:
- Weekly office visits
- Monthly client meetings
- Quarterly reviews
- Annual conferences

Currently users must create each event manually, re-entering the same details.

## Proposed Solution

### Recurrence Patterns
| Pattern | Example |
|---------|---------|
| Weekly | Every Tuesday |
| Bi-weekly | Every other Monday |
| Monthly (day) | 15th of each month |
| Monthly (weekday) | First Monday of month |
| Custom | Every 3 weeks |

### Template Approach
Rather than complex recurrence rules, use **event templates**:

1. Create template from existing event
2. Define recurrence pattern
3. System generates upcoming instances
4. Each instance is editable independently

## Data Model

### Option A: Template + Generated Instances

```python
class EventTemplate(Base, TimestampMixin):
    id: UUID
    user_id: UUID
    name: str  # "Weekly Office Visit"

    # Template data (same fields as Event)
    company_id: UUID
    location: str
    purpose: str
    default_duration_days: int

    # Recurrence
    recurrence_type: str  # weekly, biweekly, monthly_day, monthly_weekday
    recurrence_day: int  # 0-6 for weekly, 1-31 for monthly_day
    recurrence_week: int | None  # 1-4 for monthly_weekday

    # Bounds
    start_date: date
    end_date: date | None  # None = indefinite

    is_active: bool

class Event(Base):
    # ... existing fields ...
    template_id: UUID | None  # Link back to template
    is_generated: bool  # True if auto-created from template
```

### Option B: Simple Templates (No Auto-Generation)

Simpler approach - templates are just saved presets:

```python
class EventTemplate(Base):
    id: UUID
    user_id: UUID
    name: str

    # Preset values
    company_id: UUID | None
    location: str | None
    purpose: str | None
    default_duration_days: int | None
```

User manually creates events but can "Use Template" to pre-fill.

## Recommendation

**Start with Option B** (simple templates). Add recurrence logic later if needed.

Reasons:
- Much simpler implementation
- No background jobs needed
- No orphaned generated events
- Users retain full control
- Can evolve to Option A later

## UI for Option B (Simple Templates)

### Create Template
1. On Event detail: "Save as Template" button
2. Or: Settings > Event Templates > New
3. Name the template
4. Select which fields to include

### Use Template
1. On Event creation: "From Template" dropdown
2. Select template
3. Fields pre-populate
4. Adjust dates and details
5. Save as normal event

### Template Management
- Settings > Event Templates
- List, edit, delete templates
- Reorder (for dropdown order)

## UI for Option A (Auto-Generation)

### Create Recurring Event
1. Create event normally
2. Toggle "Make Recurring"
3. Select pattern (weekly, monthly, etc.)
4. Set end date or "indefinite"
5. Preview upcoming instances
6. Confirm

### Manage Instances
- List shows generated events with "recurring" badge
- Edit instance: only affects that instance
- Edit template: offers to update future instances
- Delete instance: just that one
- Delete template: asks about existing instances

### Background Job
- Daily: generate instances for next N weeks
- Clean up: remove generated instances past end_date

## Considerations

- **Conflicts**: What if generated event overlaps with manual one?
- **Modifications**: If user edits a generated event, does it detach from template?
- **Deletion**: Cascade behavior when template deleted
- **Timezone**: Recurrence based on user timezone

## API Endpoints

### Option B (Simple)
```
GET    /api/v1/event-templates
POST   /api/v1/event-templates
PUT    /api/v1/event-templates/{id}
DELETE /api/v1/event-templates/{id}
```

### Option A (Full Recurrence)
```
# Templates
GET    /api/v1/event-templates
POST   /api/v1/event-templates
PUT    /api/v1/event-templates/{id}
DELETE /api/v1/event-templates/{id}

# Instance management
GET    /api/v1/event-templates/{id}/instances?from=&to=
POST   /api/v1/event-templates/{id}/generate  # Force generation
DELETE /api/v1/event-templates/{id}/instances  # Delete all future
```

## Related
- Event management (core)
- [Calendar Integration](calendar-integration.md) - Could sync recurring events
- Todo templates (existing feature - similar concept)
