# OAuth2/OIDC Authentication

## Status
Idea - Planned for v0.3+

## Problem
Currently using simple username/password authentication. Enterprise users and those with existing identity providers (Keycloak, Authentik, etc.) want single sign-on capabilities.

## Proposed Solution
Add OAuth2/OIDC integration while keeping local auth as fallback.

## Providers to Support
- Keycloak
- Authentik
- Generic OIDC (any compliant provider)
- Google (optional)
- GitHub (optional)

## Implementation Notes

### Configuration
- Provider URL / discovery endpoint
- Client ID / Client Secret
- Scopes
- User mapping (email, display name)

### User Flow
1. User clicks "Sign in with [Provider]"
2. Redirected to identity provider
3. After auth, redirected back with token
4. App creates/updates local user record
5. Session established

### Considerations
- Keep local auth as fallback (for initial setup, recovery)
- Auto-provision users on first OAuth login?
- Map OAuth groups to roles? (see USER_ROLES.md)
- Handle token refresh

## Reference
- USER_ROLES.md section 7 covers OAuth integration concept
- REQUIREMENTS.md lines 30-32

## Related
- User management system
- Role-based access control
