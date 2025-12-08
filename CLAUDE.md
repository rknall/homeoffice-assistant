# CLAUDE.md - Project Guidelines for Claude Code

## Project: Travel Manager

A self-hosted web application for managing business trips, expenses, and reports with external system integrations.

## Anthropic Skills

**IMPORTANT:** This project uses Anthropic Skills for guidance. Before implementing UI components or document generation, consult the relevant skill:

```bash
# Frontend design - USE THIS for all UI work
/skill frontend-design

# For document templates (expense reports, travel reports)
/skill create documents
```

**When to use skills:**
- Starting any new UI component → `/skill frontend-design`
- Creating React components → `/skill frontend-design`
- Generating Excel/PDF templates → Check for document skills
- Styling decisions → `/skill frontend-design`

## Quick Reference

```bash
# Development - Backend
cd /Users/rknall/Development/Claude/travel-manager
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                          # Run tests
pytest --cov=src --cov-report=html  # Coverage report
uvicorn src.main:app --reload   # Dev server on :8000

# Development - Frontend
cd frontend
npm install
npm run dev                     # Dev server on :5173
npm run build                   # Production build
npm run test                    # Run tests

# Docker (full stack)
docker-compose up --build
```

## Architecture

```
travel-manager/
├── src/                        # Backend (Python/FastAPI)
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings (minimal env vars)
│   ├── database.py             # SQLAlchemy setup
│   ├── security.py             # Password hashing, session management
│   ├── encryption.py           # Fernet encryption for secrets
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── company.py
│   │   ├── event.py
│   │   ├── expense.py
│   │   ├── contact.py
│   │   ├── note.py
│   │   ├── todo.py
│   │   ├── photo_reference.py
│   │   ├── integration_config.py
│   │   └── system_settings.py
│   ├── schemas/                # Pydantic request/response schemas
│   │   └── ...
│   ├── api/                    # API route handlers
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependencies (auth, db session)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # Main v1 router
│   │   │   ├── auth.py         # Login, register, session
│   │   │   ├── users.py        # User management (admin)
│   │   │   ├── events.py
│   │   │   ├── companies.py
│   │   │   ├── expenses.py
│   │   │   ├── reports.py
│   │   │   └── integrations.py # Integration config CRUD
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── event_service.py
│   │   ├── expense_service.py
│   │   ├── report_generator.py
│   │   └── integration_service.py
│   └── integrations/           # External system clients
│       ├── __init__.py
│       ├── base.py             # Abstract base classes
│       ├── registry.py         # Integration type registry
│       ├── paperless.py        # Paperless-ngx client
│       └── immich.py           # Immich client (v0.2)
├── frontend/                   # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                # API client (fetch wrapper)
│   │   ├── components/         # Reusable UI components
│   │   │   ├── ui/             # Base components (Button, Input, etc.)
│   │   │   ├── layout/         # Layout components
│   │   │   └── forms/          # Form components
│   │   ├── pages/              # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Events.tsx
│   │   │   ├── EventDetail.tsx
│   │   │   ├── Expenses.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── Login.tsx
│   │   │   └── Setup.tsx       # First-run setup
│   │   ├── hooks/              # Custom React hooks
│   │   ├── stores/             # State management (zustand)
│   │   └── types/              # TypeScript types
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   ├── test_services/
│   │   └── test_integrations/
│   ├── integration/
│   │   └── test_api/
│   └── fixtures/               # Test data
├── alembic/                    # Database migrations
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── REQUIREMENTS.md             # Full requirements document
├── CLAUDE.md                   # This file
└── README.md
```

## Tech Stack & Dependencies

### Backend
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (sync for simplicity)
- **Validation:** Pydantic v2
- **Database:** SQLite (dev), PostgreSQL (prod)
- **Migrations:** Alembic
- **HTTP Client:** httpx (for external APIs)
- **Excel:** openpyxl
- **Encryption:** cryptography (Fernet)
- **Auth:** passlib[bcrypt], python-jose (for future JWT)
- **Testing:** pytest, pytest-cov, respx

### Frontend
- **Framework:** React 18
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State:** Zustand (lightweight)
- **Forms:** React Hook Form + Zod
- **HTTP:** fetch (native, with wrapper)
- **Build:** Vite
- **Testing:** Vitest + Testing Library

## Configuration Strategy

**Minimal environment variables - most config lives in the database.**

### Environment Variables (required)
```bash
# .env
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>  # REQUIRED
DATABASE_URL=sqlite:///./data/travel_manager.db       # Optional, has default
```

### Database-stored Configuration
Everything else is configured via the UI and stored encrypted in `IntegrationConfig` and `SystemSettings` tables:
- Paperless-ngx connection (URL, token, custom field name)
- Immich connection (URL, API key)
- SMTP settings (host, port, credentials)
- Default integration selections

### Encryption
Integration secrets are encrypted using Fernet symmetric encryption:
```python
# src/encryption.py
from cryptography.fernet import Fernet
from src.config import settings

def get_fernet() -> Fernet:
    # Derive key from SECRET_KEY
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.secret_key.encode()).digest()
    )
    return Fernet(key)

def encrypt_config(config: dict) -> str:
    return get_fernet().encrypt(json.dumps(config).encode()).decode()

def decrypt_config(encrypted: str) -> dict:
    return json.loads(get_fernet().decrypt(encrypted.encode()).decode())
```

## Authentication (v0.1)

### First-Run Flow
1. App starts, checks if any users exist
2. If no users → redirect to `/setup`
3. First user registration creates admin account
4. System sets `first_run_complete` in SystemSettings
5. Subsequent registrations disabled unless admin enables them

### Session-Based Auth
```python
# Session stored in secure cookie
# Backend validates session on each request

@router.post("/auth/login")
def login(credentials: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    session_token = auth_service.create_session(db, user.id)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,  # In production
        samesite="lax",
        max_age=86400 * 7  # 7 days
    )
    return {"user": UserResponse.from_orm(user)}
```

## Integration Architecture

### Plugin-like Design
Integrations follow a provider pattern for extensibility:

```python
# src/integrations/base.py
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class IntegrationProvider(ABC):
    """Base class for all integrations."""
    
    @classmethod
    @abstractmethod
    def get_type(cls) -> str:
        """Unique identifier for this integration type."""
        ...
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict:
        """JSON Schema for configuration form generation."""
        ...
    
    @abstractmethod
    def __init__(self, config: dict):
        """Initialize with decrypted config."""
        ...
    
    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity. Returns (success, message)."""
        ...


class DocumentProvider(IntegrationProvider):
    """Interface for document management systems (Paperless, etc.)"""
    
    @abstractmethod
    async def list_storage_paths(self) -> list[dict]:
        """List available storage paths."""
        ...
    
    @abstractmethod
    async def list_tags(self) -> list[dict]:
        """List all tags."""
        ...
    
    @abstractmethod
    async def create_tag(self, name: str) -> dict:
        """Create a new tag."""
        ...
    
    @abstractmethod
    async def get_documents(
        self, 
        tag_id: int | None = None,
        storage_path_id: int | None = None,
        custom_field_value: str | None = None
    ) -> list[dict]:
        """Query documents with filters."""
        ...
    
    @abstractmethod
    async def download_document(self, doc_id: int) -> tuple[bytes, str]:
        """Download document. Returns (content, filename)."""
        ...


# src/integrations/registry.py
class IntegrationRegistry:
    _providers: dict[str, type[IntegrationProvider]] = {}
    
    @classmethod
    def register(cls, provider_class: type[IntegrationProvider]):
        cls._providers[provider_class.get_type()] = provider_class
    
    @classmethod
    def get_provider(cls, integration_type: str) -> type[IntegrationProvider] | None:
        return cls._providers.get(integration_type)
    
    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._providers.keys())
```

### Paperless-ngx Implementation
```python
# src/integrations/paperless.py
class PaperlessProvider(DocumentProvider):
    
    @classmethod
    def get_type(cls) -> str:
        return "paperless"
    
    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "required": ["url", "token", "custom_field_name"],
            "properties": {
                "url": {
                    "type": "string",
                    "title": "Paperless URL",
                    "description": "Base URL of your Paperless-ngx instance",
                    "format": "uri"
                },
                "token": {
                    "type": "string",
                    "title": "API Token",
                    "description": "API token from Paperless-ngx",
                    "format": "password"
                },
                "custom_field_name": {
                    "type": "string",
                    "title": "Event Field Name",
                    "description": "Name of the custom field used to tag documents with event names",
                    "default": "Trip"
                }
            }
        }
    
    def __init__(self, config: dict):
        self.url = config["url"].rstrip("/")
        self.token = config["token"]
        self.custom_field_name = config["custom_field_name"]
        self._client = httpx.AsyncClient(
            base_url=self.url,
            headers={"Authorization": f"Token {self.token}"}
        )
    
    async def health_check(self) -> tuple[bool, str]:
        try:
            resp = await self._client.get("/api/")
            if resp.status_code == 200:
                return True, "Connected"
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)
    
    # ... implement other methods
```

## Frontend Guidelines

### Use Anthropic Skills!
Before writing any UI component, run `/skill frontend-design` to get current best practices.

### Component Structure
```tsx
// components/ui/Button.tsx
import { ButtonHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'rounded-md font-medium transition-colors',
          // Size variants
          size === 'sm' && 'px-3 py-1.5 text-sm',
          size === 'md' && 'px-4 py-2 text-base',
          size === 'lg' && 'px-6 py-3 text-lg',
          // Color variants
          variant === 'primary' && 'bg-blue-600 text-white hover:bg-blue-700',
          variant === 'secondary' && 'bg-gray-200 text-gray-900 hover:bg-gray-300',
          variant === 'danger' && 'bg-red-600 text-white hover:bg-red-700',
          className
        )}
        {...props}
      />
    );
  }
);
```

### API Client Pattern
```typescript
// api/client.ts
const API_BASE = '/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    credentials: 'include', // Important for session cookies
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) => 
    request<T>(path, { method: 'POST', body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) => 
    request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  delete: <T>(path: string) => 
    request<T>(path, { method: 'DELETE' }),
};
```

### State Management with Zustand
```typescript
// stores/auth.ts
import { create } from 'zustand';
import { api } from '@/api/client';

interface User {
  id: string;
  username: string;
  email: string;
  isAdmin: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  
  login: async (username, password) => {
    const { user } = await api.post<{ user: User }>('/auth/login', { username, password });
    set({ user });
  },
  
  logout: async () => {
    await api.post('/auth/logout', {});
    set({ user: null });
  },
  
  checkSession: async () => {
    try {
      const { user } = await api.get<{ user: User }>('/auth/me');
      set({ user, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },
}));
```

## Database Patterns

### Models with Timestamps
```python
# src/models/base.py
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### Integration Config Model
```python
# src/models/integration_config.py
from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.models.base import Base, TimestampMixin

class IntegrationConfig(Base, TimestampMixin):
    __tablename__ = "integration_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_type = Column(String(50), nullable=False)  # 'paperless', 'immich', 'smtp'
    name = Column(String(100), nullable=False)  # User-friendly name
    config_encrypted = Column(Text, nullable=False)  # Fernet-encrypted JSON
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
```

## Testing Requirements

### Unit Tests
- Every service method
- Every integration client method (with mocked HTTP)
- Encryption/decryption
- Auth logic

### Integration Tests
- Every API endpoint
- Auth flows (login, logout, session check)
- First-run setup flow
- Integration config CRUD

### Frontend Tests
- Component rendering
- Form validation
- API error handling
- Auth state management

### Mocking External Services
```python
# tests/conftest.py
import pytest
from respx import MockRouter

@pytest.fixture
def mock_paperless(respx_mock: MockRouter):
    respx_mock.get("http://paperless.test/api/").respond(200, json={})
    respx_mock.get("http://paperless.test/api/storage_paths/").respond(200, json={
        "results": [
            {"id": 1, "name": "Employer A", "path": "employer_a"},
            {"id": 2, "name": "Third Party B", "path": "third_party_b"},
        ]
    })
    return respx_mock
```

## Implementation Order (v0.1)

1. **Project Setup**
   - [x] pyproject.toml, Dockerfile (done)
   - [ ] Create src/ directory structure
   - [ ] src/config.py (minimal)
   - [ ] src/encryption.py
   - [ ] src/database.py

2. **Database Models**
   - [ ] All models as specified
   - [ ] Alembic init + first migration

3. **Authentication**
   - [ ] User model with password hashing
   - [ ] Session management
   - [ ] First-run detection
   - [ ] Auth API endpoints

4. **Integration Framework**
   - [ ] Base classes
   - [ ] Registry
   - [ ] IntegrationConfig CRUD
   - [ ] Paperless provider

5. **Core API**
   - [ ] Companies (with storage path selection)
   - [ ] Events
   - [ ] Expenses

6. **Report Generation**
   - [ ] Expense report service
   - [ ] Excel generation
   - [ ] ZIP packaging
   - [ ] Download endpoint

7. **Frontend**
   - [ ] `/skill frontend-design` first!
   - [ ] Project setup (Vite, Tailwind)
   - [ ] Auth pages (Login, Setup)
   - [ ] Layout and navigation
   - [ ] Settings / Integrations page
   - [ ] Company management
   - [ ] Event list and detail
   - [ ] Expense management
   - [ ] Report generation UI

8. **Testing**
   - [ ] Unit tests alongside development
   - [ ] Integration tests for API
   - [ ] Frontend component tests

## Do NOT

- Put integration credentials in environment variables (except SECRET_KEY)
- Skip the frontend-design skill for UI work
- Store passwords in plain text
- Use `*` imports
- Put business logic in route handlers
- Skip tests

## Do

- Use `/skill frontend-design` before any UI work
- Encrypt all sensitive configuration
- Use dependency injection
- Write tests as you build
- Keep the integration provider pattern for extensibility
- Use TypeScript strictly (no `any`)
- The demo site is hosted at port 8123 when started, admin username should be roland and admin password should be pass123!
- DO NOT PLAY AROUND WITH .env SECRET_KEY. This leads to backups no longer being compatible and data going missing between test runs. Stick with ONE key and NEVER modify it. If the user asks you to set a new Secret_key, do that only ONCE but also WARN the user about the incompatibility it might cause.
- **ALWAYS update RELEASENOTES.md** when adding new features or making substantial changes to existing features (see Release Notes section below)

## Release Notes

**IMPORTANT:** The file `RELEASENOTES.md` must be updated whenever:
- A new feature is added
- Substantial changes are made to existing features
- Bug fixes are committed
- Breaking changes are introduced

### Format
Each entry should include:
- Feature/change description
- Commit hash (6-8 characters) in parentheses, e.g., `(abc1234)`
- Categorize under: Major Features, Improvements, or Bug Fixes

### Example Entry
```markdown
#### Feature Name (`abc1234`)
- Brief description of the feature
- Key capabilities or changes
```

### When to Update
- After committing a feature, immediately add it to RELEASENOTES.md
- Group related commits under a single feature entry
- Keep the "In Development" version at the top until release
- Releasenotes should always be commited WITH the commit they reference