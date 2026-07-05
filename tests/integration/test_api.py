# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
import os

# Set test environment
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars!"  # noqa: S105
os.environ["DATABASE_URL"] = "sqlite:///./test.db"


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test that health endpoint returns OK."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthAPI:
    """Test authentication API endpoints."""

    def test_status_no_users(self, client):
        """Test auth status when no users exist."""
        response = client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["first_run"] is True
        assert data["registration_enabled"] is True

    def test_status_with_users(self, client, test_user):
        """Test auth status when users exist."""
        response = client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["first_run"] is False

    def test_register_first_user(self, client):
        """Test registering the first user."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == "newuser"
        # First user gets Global Admin role with all permissions
        assert "permissions" in data["user"]

    def test_register_duplicate_username(self, client):
        """Test registering with duplicate username fails."""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )

        # Try to register with same username (registration is still allowed for
        # first user scenario)
        # After first user, registration is disabled, so we test during first run
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "password123",
            },
        )

        # Registration is disabled after first user, so we get 403
        assert response.status_code == 403

    def test_login_valid(self, client, test_user):
        """Test login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "testuser"
        assert "session" in response.cookies

    def test_login_invalid(self, client, test_user):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    def test_me_authenticated(self, authenticated_client):
        """Test getting current user when authenticated."""
        response = authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "testuser"

    def test_me_unauthenticated(self, client):
        """Test getting current user when not authenticated."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_logout(self, authenticated_client):
        """Test logging out."""
        response = authenticated_client.post("/api/v1/auth/logout")

        assert response.status_code == 204


class TestCompaniesAPI:
    """Test companies API endpoints."""

    def test_list_companies_empty(self, authenticated_client):
        """Test listing companies when none exist."""
        response = authenticated_client.get("/api/v1/companies")

        assert response.status_code == 200
        assert response.json() == []

    def test_create_company(self, authenticated_client):
        """Test creating a company."""
        response = authenticated_client.post(
            "/api/v1/companies",
            json={
                "name": "Test Company",
                "type": "employer",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Company"
        assert data["type"] == "employer"
        assert "id" in data

    def test_get_company(self, authenticated_client):
        """Test getting a company by ID."""
        # Create company first
        create_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = create_response.json()["id"]

        # Get company
        response = authenticated_client.get(f"/api/v1/companies/{company_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Test Company"

    def test_update_company(self, authenticated_client):
        """Test updating a company."""
        # Create company first
        create_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = create_response.json()["id"]

        # Update company
        response = authenticated_client.put(
            f"/api/v1/companies/{company_id}",
            json={"name": "Updated Company", "type": "third_party"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Company"
        assert response.json()["type"] == "third_party"

    def test_delete_company(self, authenticated_client):
        """Test deleting a company."""
        # Create company first
        create_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = create_response.json()["id"]

        # Delete company
        response = authenticated_client.delete(f"/api/v1/companies/{company_id}")

        assert response.status_code == 204

        # Verify deletion
        response = authenticated_client.get(f"/api/v1/companies/{company_id}")
        assert response.status_code == 404


class TestEventsAPI:
    """Test events API endpoints."""

    def test_create_event(self, authenticated_client):
        """Test creating an event."""
        # Create company first
        company_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = company_response.json()["id"]

        # Create event
        response = authenticated_client.post(
            "/api/v1/events",
            json={
                "name": "Test Event",
                "company_id": company_id,
                "start_date": "2024-01-15",
                "end_date": "2024-01-20",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Event"
        # Status is computed from dates: Jan 15-20, 2024 is in the past
        assert data["status"] == "past"
        assert "id" in data

    def test_list_events(self, authenticated_client):
        """Test listing events."""
        # Create company and event
        company_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = company_response.json()["id"]

        authenticated_client.post(
            "/api/v1/events",
            json={
                "name": "Test Event",
                "company_id": company_id,
                "start_date": "2024-01-15",
                "end_date": "2024-01-20",
            },
        )

        # List events
        response = authenticated_client.get("/api/v1/events")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Event"


class TestExpensesAPI:
    """Test expenses API endpoints."""

    def test_create_expense(self, authenticated_client):
        """Test creating an expense."""
        # Create company and event first
        company_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = company_response.json()["id"]

        event_response = authenticated_client.post(
            "/api/v1/events",
            json={
                "name": "Test Event",
                "company_id": company_id,
                "start_date": "2024-01-15",
                "end_date": "2024-01-20",
            },
        )
        event_id = event_response.json()["id"]

        # Create expense
        response = authenticated_client.post(
            f"/api/v1/events/{event_id}/expenses",
            json={
                "date": "2024-01-16",
                "amount": 50.00,
                "currency": "EUR",
                "payment_type": "cash",
                "category": "meals",
                "description": "Lunch",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 50.00
        assert data["category"] == "meals"

    def test_list_expenses(self, authenticated_client):
        """Test listing expenses for an event."""
        # Create company, event, and expense
        company_response = authenticated_client.post(
            "/api/v1/companies",
            json={"name": "Test Company", "type": "employer"},
        )
        company_id = company_response.json()["id"]

        event_response = authenticated_client.post(
            "/api/v1/events",
            json={
                "name": "Test Event",
                "company_id": company_id,
                "start_date": "2024-01-15",
                "end_date": "2024-01-20",
            },
        )
        event_id = event_response.json()["id"]

        authenticated_client.post(
            f"/api/v1/events/{event_id}/expenses",
            json={
                "date": "2024-01-16",
                "amount": 50.00,
                "currency": "EUR",
                "payment_type": "cash",
                "category": "meals",
            },
        )

        # List expenses
        response = authenticated_client.get(f"/api/v1/events/{event_id}/expenses")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestIntegrationsAPI:
    """Test integrations API endpoints."""

    def test_list_integration_types(self, admin_client):
        """Test listing available integration types."""
        response = admin_client.get("/api/v1/integrations/types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any(t["type"] == "paperless" for t in data)

    def test_create_integration_admin_only(self, authenticated_client):
        """Test that non-admin users cannot create integrations."""
        response = authenticated_client.post(
            "/api/v1/integrations",
            json={
                "name": "Test Paperless",
                "integration_type": "paperless",
                "config": {
                    "url": "https://paperless.example.com",
                    "token": "test-token",
                    "custom_field_name": "Trip",
                },
            },
        )

        assert response.status_code == 403

    def test_create_integration_as_admin(self, admin_client):
        """Test creating an integration as admin."""
        response = admin_client.post(
            "/api/v1/integrations",
            json={
                "name": "Test Paperless",
                "integration_type": "paperless",
                "config": {
                    "url": "https://paperless.example.com",
                    "token": "test-token",
                    "custom_field_name": "Trip",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Paperless"
        assert data["integration_type"] == "paperless"


class TestExpenseScanAPI:
    """Test LLM expense scan endpoint."""

    @staticmethod
    def _create_event(client) -> str:
        company = client.post(
            "/api/v1/companies", json={"name": "ScanCo", "type": "employer"}
        ).json()
        event = client.post(
            "/api/v1/events",
            json={
                "name": "Scan Trip",
                "company_id": company["id"],
                "start_date": "2025-05-01",
                "end_date": "2025-05-02",
            },
        ).json()
        return event["id"]

    def test_llm_type_registered(self, admin_client):
        response = admin_client.get("/api/v1/integrations/types")
        assert any(t["type"] == "llm" for t in response.json())

    def test_scan_without_llm_integration(self, admin_client):
        event_id = self._create_event(admin_client)
        response = admin_client.post(
            f"/api/v1/events/{event_id}/documents/123/scan-expense"
        )
        assert response.status_code == 400
        assert "LLM integration" in response.json()["detail"]

    def test_scan_end_to_end_with_mocked_services(self, admin_client):
        import json

        import respx
        from httpx import Response

        event_id = self._create_event(admin_client)
        admin_client.post(
            "/api/v1/integrations",
            json={
                "name": "LLM",
                "integration_type": "llm",
                "config": {
                    "base_url": "https://llm.example.com/v1",
                    "api_key": "sk-test",
                    "model": "gpt-4o-mini",
                },
            },
        )
        admin_client.post(
            "/api/v1/integrations",
            json={
                "name": "Paperless",
                "integration_type": "paperless",
                "config": {
                    "url": "https://paperless.example.com",
                    "token": "test-token",
                    "custom_field_name": "Trip",
                },
            },
        )

        with respx.mock:
            respx.get("https://paperless.example.com/api/documents/42/").mock(
                return_value=Response(200, json={"content": "Taxi receipt 12.50 EUR"})
            )
            respx.post("https://llm.example.com/v1/chat/completions").mock(
                return_value=Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "content": json.dumps(
                                        {
                                            "date": "2025-05-01",
                                            "amount": 12.5,
                                            "currency": "EUR",
                                            "category": "transport",
                                            "payment_type": None,
                                            "description": "Taxi",
                                        }
                                    )
                                }
                            }
                        ]
                    },
                )
            )
            response = admin_client.post(
                f"/api/v1/events/{event_id}/documents/42/scan-expense"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2025-05-01"
        assert float(data["amount"]) == 12.5
        assert data["currency"] == "EUR"
        assert data["category"] == "transport"
        assert data["payment_type"] is None
        assert data["description"] == "Taxi"
