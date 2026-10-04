import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import admin_console  # noqa: E402
import server  # noqa: E402

OWNER_ID = "11111111-2222-3333-4444-555555555555"
STAFF_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(server, "SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.delenv("ADMIN_BOOTSTRAP_EMAILS", raising=False)
    test_client = TestClient(server.app)
    yield test_client
    test_client.app.dependency_overrides.clear()


def authenticated(client, *, user_id=OWNER_ID, email="owner@example.com"):
    client.app.dependency_overrides[admin_console._authenticated_user] = (
        lambda: {
            "user_id": user_id,
            "email": email,
            "email_confirmed": True,
        }
    )


def response(status=200, payload=None):
    if status == 204:
        return httpx.Response(status)
    return httpx.Response(status, json=payload if payload is not None else {})


def test_admin_console_page_and_client_assets_are_served(client):
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/assets/app.js").status_code == 200
    assert client.get("/admin/assets/styles.css").status_code == 200
    assert client.get("/admin/assets/not-a-real-file.js").status_code == 404


def test_admin_api_rejects_an_unauthenticated_request(client):
    result = client.get("/api/admin/me")
    assert result.status_code == 401


def test_configured_bootstrap_owner_gets_owner_access(client, monkeypatch):
    authenticated(client, email=" OWNER@example.com ")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")

    result = client.get("/api/admin/me")

    assert result.status_code == 200
    assert result.json()["role"] == "owner"
    assert "roles" in result.json()["permissions"]


def test_account_without_an_admin_role_is_denied(client, monkeypatch):
    authenticated(client)

    async def no_role(*args, **kwargs):
        return response(200, [])

    monkeypatch.setattr(admin_console, "_supabase_request", no_role)
    result = client.get("/api/admin/me")

    assert result.status_code == 403


def test_unverified_identity_cannot_use_bootstrap_access(client, monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")
    client.app.dependency_overrides[admin_console._authenticated_user] = (
        lambda: {
            "user_id": OWNER_ID,
            "email": "owner@example.com",
            "email_confirmed": False,
        }
    )

    result = client.get("/api/admin/me")

    assert result.status_code == 403


def test_finance_role_cannot_read_admin_configuration(client, monkeypatch):
    authenticated(client, user_id=STAFF_ID, email="finance@example.com")

    async def finance_role(*args, **kwargs):
        return response(200, [{"role": "finance"}])

    monkeypatch.setattr(admin_console, "_supabase_request", finance_role)
    result = client.get("/api/admin/configuration")

    assert result.status_code == 403


def test_bootstrap_owner_can_suspend_user_and_audit_the_action(
    client, monkeypatch
):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")
    calls = []

    async def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/rest/v1/admin_audit_logs":
            return response(204)
        return response(
            200, {"id": STAFF_ID, "banned_until": "2126-10-04T00:00:00Z"}
        )

    monkeypatch.setattr(admin_console, "_supabase_request", fake_request)
    result = client.patch(
        f"/api/admin/users/{STAFF_ID}/status", json={"suspended": True}
    )

    assert result.status_code == 200
    assert result.json()["id"] == STAFF_ID
    assert [call[1] for call in calls] == [
        "/rest/v1/admin_audit_logs",
        f"/auth/v1/admin/users/{STAFF_ID}",
    ]
    assert calls[1][2]["payload"] == {"ban_duration": "876000h"}


def test_admin_cannot_suspend_its_own_account(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")

    async def unexpected_request(*args, **kwargs):
        pytest.fail(
            "self-suspension must be rejected before an upstream request"
        )

    monkeypatch.setattr(admin_console, "_supabase_request", unexpected_request)
    result = client.patch(
        f"/api/admin/users/{OWNER_ID}/status", json={"suspended": True}
    )

    assert result.status_code == 409


def test_bootstrap_owner_can_verify_email_after_auditing(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")
    calls = []

    async def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/rest/v1/admin_audit_logs":
            return response(204)
        return response(
            200,
            {
                "id": STAFF_ID,
                "email_confirmed_at": "2026-10-04T00:00:00Z",
            },
        )

    monkeypatch.setattr(admin_console, "_supabase_request", fake_request)
    result = client.patch(f"/api/admin/users/{STAFF_ID}/verification")

    assert result.status_code == 200
    assert result.json()["email_confirmed"] is True
    assert calls[1][0:2] == ("PUT", f"/auth/v1/admin/users/{STAFF_ID}")
    assert calls[1][2]["payload"] == {"email_confirm": True}


def test_admin_reads_use_service_role_only_on_the_backend(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")
    requests = []

    async def fake_request(self, method, url, headers=None, **kwargs):
        requests.append((url, headers))
        if "/auth/v1/admin/users" in url:
            return httpx.Response(
                200,
                json={"users": []},
                headers={"x-total-count": "0"},
            )
        return httpx.Response(
            200,
            json=[],
            headers={"content-range": "*/0"},
        )

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request)
    result = client.get("/api/admin/overview")

    assert result.status_code == 200
    assert result.json()["users"] == 0
    assert len(requests) == 3
    assert all(
        request_headers["apikey"] == "test-service-role-key"
        for _, request_headers in requests
    )
    assert all(
        request_headers["Authorization"].startswith("Bearer ")
        for _, request_headers in requests
    )


def test_non_owner_cannot_grant_staff_roles(client, monkeypatch):
    authenticated(client, user_id=STAFF_ID, email="admin@example.com")

    async def admin_role(*args, **kwargs):
        return response(200, [{"role": "admin"}])

    monkeypatch.setattr(admin_console, "_supabase_request", admin_role)
    result = client.post(
        "/api/admin/roles",
        json={
            "user_id": OWNER_ID,
            "email": "newstaff@example.com",
            "role": "support",
        },
    )

    assert result.status_code == 403


def test_owner_cannot_grant_role_to_a_mismatched_email(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "owner@example.com")
    calls = []

    async def target_account(*args, **kwargs):
        calls.append(args)
        return response(
            200,
            {
                "id": STAFF_ID,
                "email": "different@example.com",
                "email_confirmed_at": "2026-10-01T12:00:00Z",
            },
        )

    monkeypatch.setattr(admin_console, "_supabase_request", target_account)
    result = client.post(
        "/api/admin/roles",
        json={
            "user_id": STAFF_ID,
            "email": "newstaff@example.com",
            "role": "support",
        },
    )

    assert result.status_code == 409
    assert calls == [("GET", f"/auth/v1/admin/users/{STAFF_ID}")]
