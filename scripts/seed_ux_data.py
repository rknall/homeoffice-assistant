# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Seed a fresh instance with demo data for the UX verification runs.

Uses the public API only, so it works against the dev server and the Docker
image. Run it once against an empty database:

    uv run python scripts/seed_ux_data.py --base-url http://localhost:8124
"""

import argparse
import datetime
from pathlib import Path

import httpx

ACCOUNTS = {
    "ux_admin": "ux-admin-pass-1!",
    "ux_member": "ux-member-pass-1!",
    "ux_viewer": "ux-viewer-pass-1!",
}
LOGO_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "logo.svg"
LLM_BASE_URL = "http://127.0.0.1:9/v1"
LLM_API_KEY = "ux-llm-secret-key"


def _json(response: httpx.Response) -> dict | list:
    """Return the JSON body, raising a readable error on a failed request."""
    if response.status_code >= 400:
        request = response.request
        raise RuntimeError(
            f"{request.method} {request.url.path} -> "
            f"{response.status_code}: {response.text}"
        )
    return response.json()


def _create_user(client: httpx.Client, username: str, password: str) -> dict[str, str]:
    """Create a user through ``POST /users`` and return the response body."""
    body = _json(
        client.post(
            "/api/v1/users",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": password,
            },
        )
    )
    assert isinstance(body, dict)
    return body


def _assign_roles(
    client: httpx.Client, member: dict, viewer: dict, alpha: dict
) -> None:
    """Give ux_member Member (when present) and ux_viewer only Company Viewer.

    ``POST /users`` may already have given both users Member globally; an
    existing assignment is kept instead of being added twice.
    """
    roles = _json(client.get("/api/v1/rbac/roles"))
    assert isinstance(roles, list)
    by_name = {role["name"]: role for role in roles}

    member_roles = _json(client.get(f"/api/v1/rbac/users/{member['id']}/roles"))
    assert isinstance(member_roles, list)
    has_member = any(
        a["role"]["name"] == "Member" and a["company_id"] is None for a in member_roles
    )
    if "Member" in by_name and not has_member:
        _json(
            client.post(
                f"/api/v1/rbac/users/{member['id']}/roles",
                json={"role_id": by_name["Member"]["id"]},
            )
        )

    viewer_role = by_name["Company Viewer"]
    _json(
        client.post(
            f"/api/v1/rbac/users/{viewer['id']}/roles",
            json={"role_id": viewer_role["id"], "company_id": alpha["id"]},
        )
    )
    assignments = _json(client.get(f"/api/v1/rbac/users/{viewer['id']}/roles"))
    assert isinstance(assignments, list)
    for assignment in assignments:
        if (
            assignment["role_id"] == viewer_role["id"]
            and assignment["company_id"] == alpha["id"]
        ):
            continue
        params = (
            {"company_id": assignment["company_id"]} if assignment["company_id"] else {}
        )
        response = client.delete(
            f"/api/v1/rbac/users/{viewer['id']}/roles/{assignment['role_id']}",
            params=params,
        )
        if response.status_code != 204:
            _json(response)


def _seed_events(client: httpx.Client, alpha: dict, beta: dict) -> None:
    """Create two events with expenses, notes and todos."""
    today = datetime.date.today()
    events = [
        ("Alpha Conference", alpha, today - datetime.timedelta(days=2), 3),
        ("Beta Site Visit", beta, today + datetime.timedelta(days=10), 2),
    ]
    created = []
    for name, company, start, length in events:
        event = _json(
            client.post(
                "/api/v1/events",
                json={
                    "name": name,
                    "description": f"UX demo event for {company['name']}",
                    "company_id": company["id"],
                    "start_date": start.isoformat(),
                    "end_date": (start + datetime.timedelta(days=length)).isoformat(),
                    "city": "Vienna",
                    "country": "Austria",
                    "country_code": "AT",
                },
            )
        )
        assert isinstance(event, dict)
        created.append(event)

    first, second = created
    expense_specs = [
        (first, "Train ticket", "travel", "credit_card", "120.50", "EUR", False),
        (first, "Hotel", "accommodation", "company_card", "310.00", "USD", False),
        (first, "Private dinner", "meals", "cash", "45.00", "EUR", True),
        (first, "Taxi", "transport", "cash", "28.40", "EUR", False),
        (second, "Parking", "transport", "cash", "12.00", "EUR", False),
    ]
    expenses = []
    for (
        event,
        description,
        category,
        payment,
        amount,
        currency,
        private,
    ) in expense_specs:
        expense = _json(
            client.post(
                f"/api/v1/events/{event['id']}/expenses",
                json={
                    "date": event["start_date"],
                    "amount": amount,
                    "currency": currency,
                    "payment_type": payment,
                    "category": category,
                    "description": description,
                    "is_private": private,
                },
            )
        )
        assert isinstance(expense, dict)
        expenses.append(expense)

    # The Taxi expense is the reimbursed one.
    _json(
        client.put(
            f"/api/v1/events/{first['id']}/expenses/{expenses[3]['id']}",
            json={"status": "reimbursed"},
        )
    )

    for event in created:
        _json(
            client.post(
                f"/api/v1/events/{event['id']}/notes",
                json={
                    "content": f"Remember the badge for {event['name']}",
                    "note_type": "observation",
                },
            )
        )
        for title, category in (
            ("Book hotel", "accommodation"),
            ("Pack laptop", "equipment"),
        ):
            _json(
                client.post(
                    f"/api/v1/events/{event['id']}/todos",
                    json={"title": title, "category": category},
                )
            )


def seed(client: httpx.Client) -> dict[str, str]:
    """Seed demo data through the public API and return the credentials.

    Args:
        client: An httpx client (or FastAPI TestClient) pointed at an empty
            instance. It holds the admin session cookie afterwards.

    Returns:
        Mapping of username to password for the three UX accounts.
    """
    _json(
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "ux_admin",
                "email": "ux_admin@example.com",
                "password": ACCOUNTS["ux_admin"],
                "full_name": "UX Admin",
            },
        )
    )
    member = _create_user(client, "ux_member", ACCOUNTS["ux_member"])
    viewer = _create_user(client, "ux_viewer", ACCOUNTS["ux_viewer"])

    alpha = _json(
        client.post("/api/v1/companies", json={"name": "Alpha", "type": "employer"})
    )
    beta = _json(
        client.post("/api/v1/companies", json={"name": "Beta", "type": "third_party"})
    )
    assert isinstance(alpha, dict)
    assert isinstance(beta, dict)

    _json(
        client.post(
            f"/api/v1/companies/{beta['id']}/logo",
            files={"file": ("logo.svg", LOGO_PATH.read_bytes(), "image/svg+xml")},
        )
    )

    _assign_roles(client, member, viewer, alpha)
    _seed_events(client, alpha, beta)

    _json(
        client.post(
            "/api/v1/holiday-calendars",
            json={"country_code": "AT", "display_label": "AT"},
        )
    )
    _json(
        client.post(
            "/api/v1/integrations",
            json={
                "integration_type": "llm",
                "name": "UX LLM",
                "config": {
                    "base_url": LLM_BASE_URL,
                    "api_key": LLM_API_KEY,
                    "model": "ux-model",
                },
            },
        )
    )

    return dict(ACCOUNTS)


def main() -> None:
    """Run the seed against ``--base-url`` and print the credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        credentials = seed(client)
    print("Seeded. Credentials:")
    for username, password in credentials.items():
        print(f"  {username} / {password}")


if __name__ == "__main__":
    main()
