"""Admin API with server-side role checks and service-role isolation."""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)
admin_router = APIRouter()
STATIC_DIR = Path(__file__).parent / "admin_static"


def _backend():
    import server

    return server


ROLE_PERMISSIONS = {
    "admin": {
        "analytics",
        "users",
        "user_access",
        "content",
        "finance",
        "support",
        "configuration",
        "audit",
    },
    "support": {"analytics", "users", "support", "audit"},
    "analyst": {"analytics", "finance", "audit"},
    "content": {"analytics", "content", "configuration", "audit"},
    "finance": {"analytics", "finance", "audit"},
}


def _service_key() -> str:
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _bootstrap_emails() -> set[str]:
    return {
        email.strip().casefold()
        for email in os.environ.get("ADMIN_BOOTSTRAP_EMAILS", "").split(",")
        if email.strip()
    }


def _require_service() -> str:
    key = _service_key()
    if not _backend().SUPABASE_URL or not key:
        logger.error("Admin API is missing Supabase service configuration")
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin service is not configured. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY on the backend."
            ),
        )
    return key


async def _supabase_request(
    method: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    payload: Any = None,
    prefer: Optional[str] = None,
) -> httpx.Response:
    key = _require_service()
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    try:
        backend = _backend()
        async with httpx.AsyncClient(
            timeout=backend.UPSTREAM_TIMEOUT_SECONDS
        ) as client:
            response = await client.request(
                method,
                f"{backend.SUPABASE_URL}{path}",
                headers=headers,
                params=params,
                json=payload,
            )
    except httpx.HTTPError as error:
        logger.error(
            "Admin Supabase request failed (method=%s path=%s error_type=%s)",
            method,
            path,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Admin data service is temporarily unavailable.",
        ) from error
    if response.status_code >= 500 or response.status_code in (401, 403):
        logger.error(
            "Admin Supabase request rejected (method=%s path=%s status=%s)",
            method,
            path,
            response.status_code,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin data service is not available. Check its schema and "
                "service configuration."
            ),
        )
    return response


def _response_json(response: httpx.Response, *, expected: type = list) -> Any:
    if response.status_code not in (200, 201, 204):
        logger.error(
            "Admin Supabase operation failed (status=%s)", response.status_code
        )
        raise HTTPException(
            status_code=502,
            detail="The admin operation could not be completed.",
        )
    if response.status_code == 204 or not response.content:
        return [] if expected is list else {}
    try:
        data = response.json()
    except ValueError as error:
        logger.error(
            "Admin Supabase response was not JSON (status=%s)",
            response.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail="The admin data service returned an invalid response.",
        ) from error
    if not isinstance(data, expected):
        logger.error(
            "Admin Supabase response had invalid shape (expected=%s)",
            expected.__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="The admin data service returned an invalid response.",
        )
    return data


async def _rows(table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    response = await _supabase_request(
        "GET", f"/rest/v1/{table}", params=params, prefer="count=exact"
    )
    return _response_json(response)


async def _write_audit(
    actor: dict[str, Any],
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_audit_logs",
        payload={
            "actor_id": actor["user_id"],
            "actor_email": actor.get("email") or "",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
        },
        prefer="return=minimal",
    )
    _response_json(response, expected=dict)


async def _authenticated_user(
    authorization: Optional[str] = Header(None),
) -> dict[str, Any]:
    return await _backend().get_authenticated_user(authorization)


async def require_admin(
    user: dict = Depends(_authenticated_user),
) -> dict[str, Any]:
    email = str(user.get("email") or "").strip().casefold()
    if not email or not user.get("email_confirmed"):
        raise HTTPException(
            status_code=403,
            detail="An email-verified admin identity is required.",
        )
    if email in _bootstrap_emails():
        return {
            **user,
            "email": email,
            "role": "owner",
            "permissions": set(ROLE_PERMISSIONS["admin"]) | {"roles"},
        }

    response = await _supabase_request(
        "GET",
        "/rest/v1/admin_roles",
        params={
            "select": "user_id,email,role,active",
            "user_id": f"eq.{user['user_id']}",
            "active": "eq.true",
            "limit": "1",
        },
    )
    rows = _response_json(response)
    if not rows:
        raise HTTPException(
            status_code=403, detail="This account does not have admin access."
        )
    role = rows[0].get("role")
    if role not in ROLE_PERMISSIONS:
        logger.error(
            "Invalid admin role stored for user_id=%s", user["user_id"]
        )
        raise HTTPException(
            status_code=403, detail="This account does not have admin access."
        )
    return {
        **user,
        "email": email,
        "role": role,
        "permissions": ROLE_PERMISSIONS[role],
    }


def require_permission(permission: str):
    async def dependency(
        admin: dict = Depends(require_admin),
    ) -> dict[str, Any]:
        if permission not in admin["permissions"]:
            raise HTTPException(
                status_code=403,
                detail="Your admin role does not permit this action.",
            )
        return admin

    return dependency


class ContentInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content_type: Literal["banner", "category", "announcement"]
    body: str = Field(default="", max_length=4000)
    status: Literal["draft", "review"] = "draft"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank.")
        return value


class AnnouncementInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    audience: Literal["all", "active_30d", "unverified"] = "all"

    @field_validator("title", "body")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class TicketInput(BaseModel):
    requester_email: str = Field(
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"

    @field_validator("subject")
    @classmethod
    def clean_subject(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subject cannot be blank.")
        return value


class TicketUpdate(BaseModel):
    status: Optional[Literal["open", "in_progress", "resolved"]] = None
    priority: Optional[Literal["low", "normal", "high", "urgent"]] = None
    assigned_to: Optional[UUID] = None


class ConfigInput(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_.-]{1,79}$")
    value: Any


class RoleInput(BaseModel):
    user_id: UUID
    email: str = Field(
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    role: Literal["admin", "support", "analyst", "content", "finance"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


@admin_router.get("/admin", include_in_schema=False)
async def admin_page():
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "Content-Security-Policy": "; ".join(
                (
                    "default-src 'self'",
                    "script-src 'self'",
                    "style-src 'self'",
                    "img-src 'self' data:",
                    "connect-src 'self' https://*.supabase.co "
                    "wss://*.supabase.co",
                    "base-uri 'none'",
                    "frame-ancestors 'none'",
                    "form-action 'self'",
                )
            ),
        },
    )


@admin_router.get("/admin/assets/{asset_name}", include_in_schema=False)
async def admin_asset(asset_name: str):
    if asset_name not in {
        "app.js",
        "styles.css",
        "supabase.min.js",
        "SUPABASE-LICENSE.txt",
    }:
        raise HTTPException(status_code=404, detail="Asset not found.")
    media_type = (
        "text/javascript"
        if asset_name.endswith(".js")
        else "text/plain" if asset_name.endswith(".txt") else "text/css"
    )
    return FileResponse(
        STATIC_DIR / asset_name,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@admin_router.get("/api/admin/config")
async def admin_public_config():
    backend = _backend()
    if not backend.SUPABASE_URL or not backend.SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin sign-in is not configured on this server.",
        )
    return {
        "supabase_url": backend.SUPABASE_URL,
        "supabase_anon_key": backend.SUPABASE_ANON_KEY,
    }


@admin_router.get("/api/admin/me")
async def admin_me(admin: dict = Depends(require_admin)):
    return {
        "id": admin["user_id"],
        "email": admin["email"],
        "role": admin["role"],
        "permissions": sorted(admin["permissions"]),
    }


async def _auth_users(
    page: int, per_page: int
) -> tuple[list[dict[str, Any]], Optional[int]]:
    response = await _supabase_request(
        "GET",
        "/auth/v1/admin/users",
        params={"page": page, "per_page": per_page},
    )
    payload = _response_json(response, expected=dict)
    users = payload.get("users")
    if not isinstance(users, list):
        logger.error("Supabase admin users response omitted users list")
        raise HTTPException(
            status_code=502,
            detail="The user directory returned an invalid response.",
        )
    total_header = (
        response.headers.get("x-total-count")
        or response.headers.get("content-range", "").split("/")[-1]
    )
    try:
        total = (
            int(total_header) if total_header and total_header != "*" else None
        )
    except ValueError:
        total = None
    return users, total


@admin_router.get("/api/admin/overview")
async def admin_overview(
    admin: dict = Depends(require_permission("analytics")),
):
    users, user_total = await _auth_users(1, 100)
    businesses_response = await _supabase_request(
        "GET",
        "/rest/v1/business_profiles",
        params={"select": "id", "limit": "1"},
        prefer="count=exact",
    )
    transactions_response = await _supabase_request(
        "GET",
        "/rest/v1/transactions",
        params={"select": "id", "limit": "1"},
        prefer="count=exact",
    )

    def count(response: httpx.Response) -> Optional[int]:
        value = response.headers.get("content-range", "").split("/")[-1]
        try:
            return int(value) if value and value != "*" else None
        except ValueError:
            return None

    active_since = datetime.now(timezone.utc) - timedelta(days=30)
    active_users = sum(
        1
        for user in users
        if (last_sign_in := user.get("last_sign_in_at"))
        and _is_recent(last_sign_in, active_since)
    )
    return {
        "users": user_total,
        "active_users_30d": active_users if len(users) < 100 else None,
        "businesses": count(businesses_response),
        "ledger_transactions": count(transactions_response),
        "active_users_note": (
            "Exact only when the auth directory has fewer than 100 users."
            if len(users) >= 100
            else None
        ),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _is_recent(value: str, threshold: datetime) -> bool:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp >= threshold
    except (ValueError, TypeError):
        return False


@admin_router.get("/api/admin/users")
async def admin_users(
    page: int = Query(default=1, ge=1, le=10000),
    search: str = Query(default="", max_length=160),
    admin: dict = Depends(require_permission("users")),
):
    users, total = await _auth_users(page, 50)
    query = search.strip().casefold()
    safe_users = [
        {
            "id": user.get("id"),
            "email": user.get("email") or "",
            "created_at": user.get("created_at"),
            "last_sign_in_at": user.get("last_sign_in_at"),
            "email_confirmed": bool(user.get("email_confirmed_at")),
            "banned_until": user.get("banned_until"),
            "provider": (
                (user.get("app_metadata") or {}).get("provider") or ""
            ),
            "name": ((user.get("user_metadata") or {}).get("full_name") or ""),
        }
        for user in users
    ]
    if query:
        safe_users = [
            user
            for user in safe_users
            if query in user["email"].casefold()
            or query in user["name"].casefold()
        ]
    return {
        "users": safe_users,
        "page": page,
        "per_page": 50,
        "total": total,
        "search_scope": "current_page",
    }


@admin_router.get("/api/admin/users/{user_id}")
async def admin_user_detail(
    user_id: UUID, admin: dict = Depends(require_permission("users"))
):
    response = await _supabase_request(
        "GET", f"/auth/v1/admin/users/{user_id}"
    )
    user = _response_json(response, expected=dict)
    profile_response = await _supabase_request(
        "GET",
        "/rest/v1/business_profiles",
        params={
            "select": "id,name,updated_at",
            "user_id": f"eq.{user_id}",
            "limit": "20",
        },
    )
    profiles = _response_json(profile_response)
    return {
        "id": user.get("id"),
        "email": user.get("email") or "",
        "created_at": user.get("created_at"),
        "last_sign_in_at": user.get("last_sign_in_at"),
        "email_confirmed": bool(user.get("email_confirmed_at")),
        "banned_until": user.get("banned_until"),
        "provider": ((user.get("app_metadata") or {}).get("provider") or ""),
        "name": ((user.get("user_metadata") or {}).get("full_name") or ""),
        "businesses": profiles,
    }


class UserStatusInput(BaseModel):
    suspended: bool


@admin_router.patch("/api/admin/users/{user_id}/status")
async def admin_set_user_status(
    user_id: UUID,
    payload: UserStatusInput,
    admin: dict = Depends(require_permission("user_access")),
):
    if payload.suspended and str(user_id) == str(admin["user_id"]):
        raise HTTPException(
            status_code=409,
            detail="You cannot suspend your own admin account.",
        )
    action = "user.suspend" if payload.suspended else "user.unsuspend"
    await _write_audit(
        admin,
        action=action,
        resource_type="auth_user",
        resource_id=str(user_id),
    )
    response = await _supabase_request(
        "PUT",
        f"/auth/v1/admin/users/{user_id}",
        payload={"ban_duration": "876000h" if payload.suspended else "none"},
    )
    user = _response_json(response, expected=dict)
    return {"id": user.get("id"), "banned_until": user.get("banned_until")}


@admin_router.patch("/api/admin/users/{user_id}/verification")
async def admin_verify_user_email(
    user_id: UUID, admin: dict = Depends(require_permission("user_access"))
):
    await _write_audit(
        admin,
        action="user.verify_email",
        resource_type="auth_user",
        resource_id=str(user_id),
    )
    response = await _supabase_request(
        "PUT",
        f"/auth/v1/admin/users/{user_id}",
        payload={"email_confirm": True},
    )
    user = _response_json(response, expected=dict)
    return {
        "id": user.get("id"),
        "email_confirmed": bool(user.get("email_confirmed_at")),
    }


@admin_router.post("/api/admin/users/{user_id}/revoke-sessions")
async def admin_revoke_sessions(
    user_id: UUID, admin: dict = Depends(require_permission("user_access"))
):
    await _write_audit(
        admin,
        action="user.revoke_sessions",
        resource_type="auth_user",
        resource_id=str(user_id),
    )
    response = await _supabase_request(
        "POST",
        f"/auth/v1/admin/users/{user_id}/logout",
        params={"scope": "global"},
    )
    _response_json(response, expected=dict)
    return {"revoked": True}


@admin_router.get("/api/admin/roles")
async def list_admin_roles(admin: dict = Depends(require_permission("roles"))):
    response = await _supabase_request(
        "GET",
        "/rest/v1/admin_roles",
        params={
            "select": "user_id,email,role,active,created_at,updated_at",
            "order": "created_at.asc",
            "limit": "500",
        },
    )
    return {"roles": _response_json(response)}


@admin_router.post("/api/admin/roles")
async def grant_admin_role(
    payload: RoleInput, admin: dict = Depends(require_permission("roles"))
):
    if admin["role"] != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only a bootstrap owner can change admin roles.",
        )
    if payload.email in _bootstrap_emails():
        raise HTTPException(
            status_code=409,
            detail=(
                "Bootstrap owners are managed through backend configuration."
            ),
        )
    target_response = await _supabase_request(
        "GET", f"/auth/v1/admin/users/{payload.user_id}"
    )
    target = _response_json(target_response, expected=dict)
    if str(
        target.get("email") or ""
    ).casefold() != payload.email or not target.get("email_confirmed_at"):
        raise HTTPException(
            status_code=409,
            detail="The account UUID must match a verified account email.",
        )
    await _write_audit(
        admin,
        action="role.grant",
        resource_type="admin_role",
        resource_id=str(payload.user_id),
        details={"email": payload.email, "role": payload.role},
    )
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_roles",
        payload={
            "user_id": str(payload.user_id),
            "email": payload.email,
            "role": payload.role,
            "active": True,
            "created_by": admin["user_id"],
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    rows = _response_json(response)
    return {"role": rows[0] if rows else {}}


@admin_router.delete("/api/admin/roles/{user_id}")
async def revoke_admin_role(
    user_id: UUID, admin: dict = Depends(require_permission("roles"))
):
    if admin["role"] != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only a bootstrap owner can change admin roles.",
        )
    target = await _rows(
        "admin_roles",
        {"select": "email", "user_id": f"eq.{user_id}", "limit": "1"},
    )
    if not target:
        raise HTTPException(status_code=404, detail="Admin role not found.")
    if target[0]["email"].casefold() in _bootstrap_emails():
        raise HTTPException(
            status_code=409,
            detail=(
                "Bootstrap owners are managed through backend configuration."
            ),
        )
    await _write_audit(
        admin,
        action="role.revoke",
        resource_type="admin_role",
        resource_id=str(user_id),
    )
    response = await _supabase_request(
        "DELETE", "/rest/v1/admin_roles", params={"user_id": f"eq.{user_id}"}
    )
    _response_json(response, expected=dict)
    return {"revoked": True}


@admin_router.get("/api/admin/audit")
async def list_admin_audit(
    page: int = Query(default=1, ge=1, le=10000),
    admin: dict = Depends(require_permission("audit")),
):
    response = await _supabase_request(
        "GET",
        "/rest/v1/admin_audit_logs",
        params={
            "select": (
                "id,actor_id,actor_email,action,resource_type,resource_id,"
                "details,created_at"
            ),
            "order": "created_at.desc",
            "limit": "50",
            "offset": str((page - 1) * 50),
        },
    )
    return {"events": _response_json(response), "page": page}


@admin_router.get("/api/admin/ledger")
async def admin_ledger(
    kind: Literal["transactions", "bills"] = "transactions",
    page: int = Query(default=1, ge=1, le=10000),
    admin: dict = Depends(require_permission("finance")),
):
    table = "transactions" if kind == "transactions" else "bills"
    fields = (
        "id,user_id,party_id,amount,type,note,date,created_at"
        if kind == "transactions"
        else "id,user_id,party_id,total,status,created_at"
    )
    rows = await _rows(
        table,
        {
            "select": fields,
            "order": "created_at.desc",
            "limit": "50",
            "offset": str((page - 1) * 50),
        },
    )
    return {
        "records": rows,
        "page": page,
        "kind": kind,
        "note": (
            "CredEasy records business ledger activity; it does not process "
            "card or wallet payments."
        ),
    }


@admin_router.get("/api/admin/content")
async def list_admin_content(
    admin: dict = Depends(require_permission("content")),
):
    rows = await _rows(
        "admin_content_items",
        {"select": "*", "order": "updated_at.desc", "limit": "200"},
    )
    return {
        "items": rows,
        "delivery": (
            "Admin drafts/review items are stored centrally; the mobile app "
            "does not yet consume remote CMS content."
        ),
    }


@admin_router.post("/api/admin/content")
async def create_admin_content(
    payload: ContentInput, admin: dict = Depends(require_permission("content"))
):
    await _write_audit(
        admin, action="content.create", resource_type="content_item"
    )
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_content_items",
        payload={
            **payload.model_dump(),
            "created_by": admin["user_id"],
            "updated_by": admin["user_id"],
        },
        prefer="return=representation",
    )
    rows = _response_json(response)
    return {"item": rows[0] if rows else {}}


@admin_router.patch("/api/admin/content/{item_id}")
async def update_admin_content(
    item_id: UUID,
    payload: ContentInput,
    admin: dict = Depends(require_permission("content")),
):
    await _write_audit(
        admin,
        action="content.update",
        resource_type="content_item",
        resource_id=str(item_id),
    )
    response = await _supabase_request(
        "PATCH",
        "/rest/v1/admin_content_items",
        params={"id": f"eq.{item_id}"},
        payload={
            **payload.model_dump(),
            "updated_by": admin["user_id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        prefer="return=representation",
    )
    rows = _response_json(response)
    if not rows:
        raise HTTPException(status_code=404, detail="Content item not found.")
    return {"item": rows[0]}


@admin_router.get("/api/admin/announcements")
async def list_announcements(
    admin: dict = Depends(require_permission("content")),
):
    rows = await _rows(
        "admin_announcements",
        {"select": "*", "order": "created_at.desc", "limit": "200"},
    )
    return {
        "items": rows,
        "delivery": (
            "Drafts only; push delivery is not configured for this app."
        ),
    }


@admin_router.post("/api/admin/announcements")
async def create_announcement(
    payload: AnnouncementInput,
    admin: dict = Depends(require_permission("content")),
):
    await _write_audit(
        admin, action="announcement.draft", resource_type="announcement"
    )
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_announcements",
        payload={
            **payload.model_dump(),
            "status": "draft",
            "scheduled_at": None,
            "created_by": admin["user_id"],
        },
        prefer="return=representation",
    )
    rows = _response_json(response)
    return {
        "item": rows[0] if rows else {},
        "delivery": "Draft saved; nothing was sent.",
    }


@admin_router.get("/api/admin/tickets")
async def list_tickets(admin: dict = Depends(require_permission("support"))):
    rows = await _rows(
        "admin_support_tickets",
        {"select": "*", "order": "updated_at.desc", "limit": "200"},
    )
    return {"tickets": rows}


@admin_router.post("/api/admin/tickets")
async def create_ticket(
    payload: TicketInput, admin: dict = Depends(require_permission("support"))
):
    await _write_audit(
        admin, action="ticket.create", resource_type="support_ticket"
    )
    now = datetime.now(timezone.utc).isoformat()
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_support_tickets",
        payload={
            **payload.model_dump(),
            "created_by": admin["user_id"],
            "updated_by": admin["user_id"],
            "updated_at": now,
        },
        prefer="return=representation",
    )
    rows = _response_json(response)
    return {"ticket": rows[0] if rows else {}}


@admin_router.patch("/api/admin/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    admin: dict = Depends(require_permission("support")),
):
    update = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
    }
    if not update:
        raise HTTPException(
            status_code=400, detail="No ticket changes were provided."
        )
    update.update(
        {
            "updated_by": admin["user_id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await _write_audit(
        admin,
        action="ticket.update",
        resource_type="support_ticket",
        resource_id=str(ticket_id),
        details={"fields": sorted(update)},
    )
    response = await _supabase_request(
        "PATCH",
        "/rest/v1/admin_support_tickets",
        params={"id": f"eq.{ticket_id}"},
        payload=update,
        prefer="return=representation",
    )
    rows = _response_json(response)
    if not rows:
        raise HTTPException(
            status_code=404, detail="Support ticket not found."
        )
    return {"ticket": rows[0]}


@admin_router.get("/api/admin/configuration")
async def list_configuration(
    admin: dict = Depends(require_permission("configuration")),
):
    rows = await _rows(
        "admin_app_configuration",
        {"select": "*", "order": "key.asc", "limit": "200"},
    )
    return {
        "settings": rows,
        "delivery": (
            "Saved settings are not yet read by the mobile app; app-side "
            "rollout enforcement is not connected."
        ),
    }


@admin_router.put("/api/admin/configuration")
async def save_configuration(
    payload: ConfigInput,
    admin: dict = Depends(require_permission("configuration")),
):
    await _write_audit(
        admin,
        action="configuration.upsert",
        resource_type="app_configuration",
        resource_id=payload.key,
    )
    response = await _supabase_request(
        "POST",
        "/rest/v1/admin_app_configuration",
        payload={
            "key": payload.key,
            "value": payload.value,
            "updated_by": admin["user_id"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        prefer="resolution=merge-duplicates,return=representation",
    )
    rows = _response_json(response)
    return {"setting": rows[0] if rows else {}}


@admin_router.get("/api/admin/reports")
async def admin_reports(
    admin: dict = Depends(require_permission("analytics")),
):
    overview = await admin_overview(admin)
    users, _ = await _auth_users(1, 100)
    return {
        "overview": overview,
        "recent_users": [
            {
                "id": user.get("id"),
                "email": user.get("email") or "",
                "created_at": user.get("created_at"),
                "last_sign_in_at": user.get("last_sign_in_at"),
            }
            for user in users
        ],
        "note": (
            "User and ledger activity counts only; no platform revenue, "
            "commissions or refunds are inferred."
        ),
    }


@admin_router.get("/api/admin/capabilities")
async def admin_capabilities(admin: dict = Depends(require_admin)):
    return {
        "modules": {
            "users": "live",
            "content": "limited",
            "transactions": "read_only",
            "notifications": "draft_only",
            "reports": "live",
            "roles": (
                "live" if "roles" in admin["permissions"] else "restricted"
            ),
            "orders": "not_connected",
            "support": "live",
            "analytics": "live",
            "audit": "live",
            "configuration": "limited",
            "coupons": "not_connected",
            "vendors": "not_connected",
            "moderation": "not_connected",
            "sessions": "revoke_only",
            "versions": "not_connected",
        }
    }
