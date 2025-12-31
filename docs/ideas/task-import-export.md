# Task Import/Export Integration

## Status
Idea - Not Started

## Plugin Candidate
Yes - External task sync is optional functionality that builds on top of the core todo system.

## Problem
Users may want their event todos to sync with external task management tools they already use (Todoist, Things, etc.).

## Prerequisite
**Implemented in v0.3.0:** Internal todo management with CRUD, categories, due dates, templates, and auto-completion.

## Proposed Integrations
- Todoist
- Things 3 (macOS/iOS)
- Microsoft To Do
- Generic CalDAV tasks

## Features

### Export Todos
- Push event todos to external task manager
- Include due dates, categories
- Link back to event in description

### Import Tasks
- Import tasks from external system
- Match to events by date/tag
- Two-way completion sync

## Use Cases
- See trip preparation tasks in daily task manager
- Complete todos on mobile, sync back to app
- Use preferred task app while keeping trip context

## Implementation Notes

### Provider Interface
```python
class TaskProvider(IntegrationProvider):
    async def create_task(self, todo: Todo, event: Event) -> str
    async def update_task(self, external_id: str, completed: bool)
    async def sync_completions(self) -> list[tuple[str, bool]]
    async def delete_task(self, external_id: str)
```

### Todoist Example
```python
class TodoistProvider(TaskProvider):
    async def create_task(self, todo: Todo, event: Event) -> str:
        # Create task in Todoist project
        # Return external_id for tracking
        ...
```

### Configuration
- Provider selection
- API token
- Project/list mapping
- Sync frequency
- Sync direction (export only, import only, bidirectional)

## Data Model Extension

```python
class Todo:
    # ... existing fields ...

    # External sync tracking
    external_provider: str | None  # "todoist", "things", etc.
    external_id: str | None        # ID in external system
    last_synced_at: datetime | None
```

## Considerations
- Handle offline/conflict scenarios
- Respect rate limits
- Optional: Create project per event
- Handle deletion in either system

## Related
- Todo management (implemented in v0.3.0)
- Todo templates (implemented in v0.3.0)
- [Calendar Integration](calendar-integration.md) - Similar external sync pattern
