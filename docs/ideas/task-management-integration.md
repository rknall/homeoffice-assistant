# Task Management Integration

## Status
Idea - Not Started

## Problem
Users may want their event todos to sync with external task management tools they already use (Todoist, Things, etc.).

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

### Todoist Example
```python
class TodoistProvider(TaskProvider):
    async def create_task(self, todo: Todo, event: Event) -> str
    async def update_task(self, external_id: str, completed: bool)
    async def sync_completions(self) -> list[tuple[str, bool]]
```

### Configuration
- Provider selection
- API token
- Project/list mapping
- Sync frequency

## Considerations
- Handle offline/conflict scenarios
- Respect rate limits
- Optional: Create project per event

## Reference
- REQUIREMENTS.md line 249

## Related
- Todo templates feature
- Event todos
