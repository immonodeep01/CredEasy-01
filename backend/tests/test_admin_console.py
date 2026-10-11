import asyncio
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


def authenticated(
    client, *, user_id=OWNER_ID, email="immonodeep@gmail.com"
):
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


def test_admin_response_accepts_partial_content():
    result = admin_console._response_json(response(206, [{"id": "entry"}]))

    assert result == [{"id": "entry"}]


def test_push_registration_uses_the_verified_account_id(client, monkeypatch):
    authenticated(client, user_id=STAFF_ID, email="user@example.com")
    calls = []

    async def capture_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return response(204)

    monkeypatch.setattr(admin_console, "_supabase_request", capture_request)
    result = client.post(
        "/api/push/device",
        json={
            "expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]",
            "platform": "android",
        },
    )

    assert result.status_code == 200
    assert result.json() == {"registered": True}
    payload = calls[0][2]["payload"]
    assert payload["expo_push_token"] == "ExpoPushToken[abcdefghijklmnopqrstuv]"
    assert payload["user_id"] == STAFF_ID
    assert payload["platform"] == "android"
    assert isinstance(payload["updated_at"], str)


def test_push_registration_rejects_malformed_tokens_before_writing(client, monkeypatch):
    authenticated(client)

    async def unexpected_request(*args, **kwargs):
        pytest.fail("invalid push tokens must be rejected before persistence")

    monkeypatch.setattr(admin_console, "_supabase_request", unexpected_request)
    result = client.post(
        "/api/push/device",
        json={"expo_push_token": "not-a-token", "platform": "android"},
    )

    assert result.status_code == 422


def test_push_unregistration_is_scoped_to_the_verified_account(client, monkeypatch):
    authenticated(client, user_id=STAFF_ID, email="user@example.com")
    calls = []

    async def capture_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return response(204)

    monkeypatch.setattr(admin_console, "_supabase_request", capture_request)
    result = client.request(
        "DELETE",
        "/api/push/device",
        json={"expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]"},
    )

    assert result.status_code == 200
    assert calls[0][2]["params"] == {
        "expo_push_token": "eq.ExpoPushToken[abcdefghijklmnopqrstuv]",
        "user_id": f"eq.{STAFF_ID}",
    }


def test_push_unregistration_succeeds_when_device_table_is_not_installed(client, monkeypatch):
    authenticated(client, user_id=STAFF_ID, email="user@example.com")

    async def missing_table(*args, **kwargs):
        return response(404)

    monkeypatch.setattr(admin_console, "_supabase_request", missing_table)
    result = client.request(
        "DELETE",
        "/api/push/device",
        json={"expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]"},
    )

    assert result.status_code == 200
    assert result.json() == {"registered": False}


def test_direct_push_is_scoped_to_the_selected_account(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
    target_id = "99999999-2222-3333-4444-555555555555"
    announcement_id = "77777777-2222-3333-4444-555555555555"
    writes = []
    deliveries = []

    async def capture_request(method, path, **kwargs):
        writes.append((method, path, kwargs))
        if method == "POST" and path == "/rest/v1/admin_announcements":
            return response(201, [{"id": announcement_id}])
        return response(204)

    async def registered_devices(user_id=None):
        assert str(user_id) == target_id
        return [{"expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]"}]

    async def send_pushes(devices, **kwargs):
        deliveries.append((devices, kwargs))
        return 1, 0

    async def audit(*args, **kwargs):
        return None

    monkeypatch.setattr(admin_console, "_supabase_request", capture_request)
    monkeypatch.setattr(admin_console, "_registered_push_devices", registered_devices)
    monkeypatch.setattr(admin_console, "_send_expo_pushes", send_pushes)
    monkeypatch.setattr(admin_console, "_write_audit", audit)

    result = client.post(
        f"/api/admin/users/{target_id}/push",
        json={"title": "Store update", "body": "A new update is available."},
    )

    assert result.status_code == 200
    assert result.json() == {"status": "sent", "accepted": 1, "failed": 0}
    created = writes[0][2]["payload"]
    assert created["audience"] == "account"
    assert created["target_user_id"] == target_id
    assert deliveries[0][1]["notification_id"] == announcement_id


def test_broadcast_send_claims_only_an_all_user_draft(client, monkeypatch):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
    announcement_id = "77777777-2222-3333-4444-555555555555"
    writes = []

    async def rows(table, params):
        assert table == "admin_announcements"
        return [{
            "id": announcement_id,
            "title": "Service update",
            "body": "A new update is available.",
            "audience": "all",
            "status": "draft",
        }]

    async def capture_request(method, path, **kwargs):
        writes.append((method, path, kwargs))
        return response(200, [{"id": announcement_id}]) if method == "PATCH" and kwargs.get("prefer") == "return=representation" else response(204)

    async def registered_devices(user_id=None):
        assert user_id is None
        return [{"expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]"}]

    async def send_pushes(devices, **kwargs):
        return 1, 0

    async def audit(*args, **kwargs):
        return None

    monkeypatch.setattr(admin_console, "_rows", rows)
    monkeypatch.setattr(admin_console, "_supabase_request", capture_request)
    monkeypatch.setattr(admin_console, "_registered_push_devices", registered_devices)
    monkeypatch.setattr(admin_console, "_send_expo_pushes", send_pushes)
    monkeypatch.setattr(admin_console, "_write_audit", audit)

    result = client.post(f"/api/admin/announcements/{announcement_id}/send")

    assert result.status_code == 200
    assert result.json() == {"status": "sent", "accepted": 1, "failed": 0}
    assert writes[0][2]["params"]["status"] == "eq.draft"


def test_push_delivery_fails_closed_without_expo_access_token(monkeypatch):
    monkeypatch.delenv("EXPO_ACCESS_TOKEN", raising=False)

    with pytest.raises(admin_console.HTTPException) as error:
        asyncio.run(
            admin_console._send_expo_pushes(
                [{"expo_push_token": "ExpoPushToken[abcdefghijklmnopqrstuv]", "user_id": STAFF_ID}],
                title="Update",
                body="A new update is available.",
                notification_id="77777777-2222-3333-4444-555555555555",
            )
        )

    assert error.value.status_code == 503


@pytest.mark.parametrize(
    ("handler", "table", "response_key"),
    [
        (admin_console.list_admin_content, "admin_content_items", "items"),
        (admin_console.list_announcements, "admin_announcements", "items"),
        (admin_console.list_tickets, "admin_support_tickets", "tickets"),
        (admin_console.list_configuration, "admin_app_configuration", "settings"),
    ],
)
def test_admin_table_pages_have_a_hard_limit_and_offset(
    monkeypatch, handler, table, response_key
):
    requests = []

    async def capture_rows(requested_table, params):
        requests.append((requested_table, params))
        return []

    monkeypatch.setattr(admin_console, "_rows", capture_rows)
    result = asyncio.run(handler(page=3, admin={"user_id": OWNER_ID}))

    assert result[response_key] == []
    assert result["page"] == 3
    assert requests == [
        (
            table,
            {
                "select": "*",
                "order": (
                    "updated_at.desc"
                    if table in {"admin_content_items", "admin_support_tickets"}
                    else "created_at.desc"
                    if table == "admin_announcements"
                    else "key.asc"
                ),
                "limit": "50",
                "offset": "100",
            },
        )
    ]


def test_admin_role_list_pages_have_a_hard_limit_and_offset(monkeypatch):
    requests = []

    async def capture_request(method, path, *, params=None, **kwargs):
        requests.append((method, path, params))
        return response(200, [])

    monkeypatch.setattr(admin_console, "_supabase_request", capture_request)
    result = asyncio.run(
        admin_console.list_admin_roles(page=3, admin={"user_id": OWNER_ID})
    )

    assert result == {"roles": [], "page": 3}
    assert requests[0][2]["limit"] == "50"
    assert requests[0][2]["offset"] == "100"


def test_admin_console_page_and_client_assets_are_served(client):
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/assets/app.js").status_code == 200
    assert client.get("/admin/assets/styles.css").status_code == 200
    assert client.get("/admin/assets/not-a-real-file.js").status_code == 404


def test_admin_api_rejects_an_unauthenticated_request(client):
    result = client.get("/api/admin/me")
    assert result.status_code == 401


@pytest.mark.parametrize(
    "email",
    [" IMMONODEEP@gmail.com ", "monodeepdeb276@gmail.com"],
)
def test_configured_bootstrap_owner_gets_owner_access(client, monkeypatch, email):
    authenticated(client, email=email)
    monkeypatch.setenv(
        "ADMIN_BOOTSTRAP_EMAILS",
        "immonodeep@gmail.com,monodeepdeb276@gmail.com",
    )

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


def test_only_allowlisted_google_accounts_can_access_admin(client, monkeypatch):
    authenticated(client, email="unlisted@example.com")
    monkeypatch.setenv(
        "ADMIN_BOOTSTRAP_EMAILS",
        "immonodeep@gmail.com,monodeepdeb276@gmail.com,unlisted@example.com",
    )

    async def unexpected_request(*args, **kwargs):
        pytest.fail("unlisted accounts must be rejected before role lookup")

    monkeypatch.setattr(admin_console, "_supabase_request", unexpected_request)
    result = client.get("/api/admin/me")

    assert result.status_code == 403
    assert result.json()["detail"] == (
        "This Google account is not allowed to access the admin console."
    )


def test_unverified_identity_cannot_use_bootstrap_access(client, monkeypatch):
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
    client.app.dependency_overrides[admin_console._authenticated_user] = (
        lambda: {
            "user_id": OWNER_ID,
            "email": "immonodeep@gmail.com",
            "email_confirmed": False,
        }
    )

    result = client.get("/api/admin/me")

    assert result.status_code == 403


def test_finance_role_cannot_read_admin_configuration(client, monkeypatch):
    authenticated(
        client, user_id=STAFF_ID, email="monodeepdeb276@gmail.com"
    )

    async def finance_role(*args, **kwargs):
        return response(200, [{"role": "finance"}])

    monkeypatch.setattr(admin_console, "_supabase_request", finance_role)
    result = client.get("/api/admin/configuration")

    assert result.status_code == 403


def test_bootstrap_owner_can_suspend_user_and_audit_the_action(
    client, monkeypatch
):
    authenticated(client)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
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
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")

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
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
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
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
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
    authenticated(
        client, user_id=STAFF_ID, email="monodeepdeb276@gmail.com"
    )

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
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "immonodeep@gmail.com")
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
