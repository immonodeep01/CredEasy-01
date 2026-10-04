(() => {
  "use strict";

  const MODULES = [
    { id: "overview", label: "Live analytics", icon: "◫", permission: "analytics" },
    { id: "users", label: "User management", icon: "◎", permission: "users" },
    { id: "content", label: "Content management", icon: "▤", permission: "content" },
    { id: "payments", label: "Payments & activity", icon: "↗", permission: "finance" },
    { id: "notifications", label: "Notifications", icon: "◉", permission: "content" },
    { id: "reports", label: "Reports & exports", icon: "▥", permission: "analytics" },
    { id: "roles", label: "Roles & permissions", icon: "♙", permission: "roles" },
    { id: "orders", label: "Orders & bookings", icon: "▣" },
    { id: "support", label: "Support tickets", icon: "✉", permission: "support" },
    { id: "audit", label: "Audit history", icon: "◷", permission: "audit" },
    { id: "configuration", label: "Feature configuration", icon: "⚙", permission: "configuration" },
    { id: "coupons", label: "Coupons & discounts", icon: "％" },
    { id: "vendors", label: "Vendors & partners", icon: "◇" },
    { id: "moderation", label: "Content moderation", icon: "⚑" },
    { id: "sessions", label: "Sessions & devices", icon: "⌁", permission: "user_access" },
    { id: "versions", label: "App versions", icon: "⬆" },
  ];

  const state = {
    client: null,
    session: null,
    admin: null,
    capabilities: {},
    page: "overview",
    pageNumber: 1,
    search: "",
    toastTimer: null,
  };

  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const date = (value) => {
    if (!value) return "—";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  };
  const shortDate = (value) => {
    if (!value) return "—";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleDateString();
  };
  const fmt = (value) => value === null || value === undefined ? "—" : Number(value).toLocaleString();
  const permitted = (permission) => !permission || state.admin?.permissions.includes(permission);
  const capability = (id) => state.capabilities[id === "payments" ? "transactions" : id] || "not_connected";
  const capabilityText = (status) => ({
    live: "Connected",
    limited: "Limited",
    read_only: "Read only",
    draft_only: "Drafts only",
    revoke_only: "Revoke only",
    restricted: "Role restricted",
    not_connected: "Not connected",
  })[status] || status.replaceAll("_", " ");

  function toast(message, isError = false) {
    const node = $("#toast");
    node.textContent = message;
    node.style.background = isError ? "#8d342d" : "";
    node.classList.add("visible");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => node.classList.remove("visible"), 3600);
  }

  function showLogin(message = "") {
    $("#app").hidden = true;
    $("#login").hidden = false;
    $("#login-error").hidden = !message;
    $("#login-error").textContent = message;
  }

  function showApp() {
    $("#login").hidden = true;
    $("#app").hidden = false;
    $("#admin-email").textContent = state.admin.email;
    $("#role-badge").textContent = state.admin.role;
    $("#role-badge").title = `${state.admin.permissions.length} granted permissions`;
    renderNavigation();
  }

  async function api(path, options = {}) {
    const {
      data: { session },
      error: sessionError,
    } = await state.client.auth.getSession();
    if (sessionError) throw new Error(`Could not read admin session: ${sessionError.message}`);
    state.session = session;
    if (!session?.access_token) {
      throw new Error("Your session has expired. Sign in again.");
    }
    let response;
    try {
      response = await fetch(path, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
          ...(options.headers || {}),
        },
      });
    } catch {
      throw new Error("CredEasy admin could not reach the backend. Check your connection and try again.");
    }
    const raw = await response.text();
    let body = {};
    if (raw) {
      try {
        body = JSON.parse(raw);
      } catch {
        throw new Error("The admin backend returned an unreadable response.");
      }
    }
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(body.detail || "Your account does not have this admin permission.");
      }
      throw new Error(body.detail || `Admin request failed (${response.status}).`);
    }
    return body;
  }

  async function loadCapabilities() {
    const response = await api("/api/admin/capabilities");
    state.capabilities = response.modules || {};
  }

  function renderNavigation() {
    const nav = $("#navigation");
    nav.innerHTML = MODULES.map((module) => {
      const status = capability(module.id);
      const disabled = !permitted(module.permission);
      const statusText = status === "live" ? "" : capabilityText(status);
      return `<button class="nav-link" type="button" data-page="${esc(module.id)}" aria-current="${state.page === module.id ? "page" : "false"}" ${disabled ? "disabled title=\"Not permitted for your role\"" : ""}>
        <span class="nav-icon" aria-hidden="true">${esc(module.icon)}</span><span>${esc(module.label)}</span>${statusText ? `<span class="nav-status">${esc(statusText)}</span>` : ""}
      </button>`;
    }).join("");
    nav.querySelectorAll("[data-page]").forEach((button) => {
      button.addEventListener("click", () => {
        state.page = button.dataset.page;
        state.pageNumber = 1;
        state.search = "";
        $("#sidebar").classList.remove("sidebar-open");
        renderNavigation();
        renderPage();
      });
    });
    const selected = MODULES.find((module) => module.id === state.page);
    $("#page-crumb").textContent = selected?.label || "Overview";
  }

  function heading(title, description, actions = "") {
    return `<header class="page-heading"><div><p class="eyebrow">CredEasy · Admin workspace</p><h1>${esc(title)}</h1><p>${esc(description)}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ""}</header>`;
  }

  function panel(title, body, subtitle = "", action = "") {
    return `<section class="panel"><header class="panel-header"><div><h2>${esc(title)}</h2>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</div>${action}</header>${body}</section>`;
  }

  function notice(text, type = "") {
    return `<div class="notice ${type ? `notice-${esc(type)}` : ""}">${text}</div>`;
  }

  function statusPill(value) {
    const normalized = String(value || "unknown").toLowerCase().replaceAll(" ", "_");
    const style = ["suspended", "urgent", "high"].includes(normalized) ? "status-danger"
      : ["open", "in_progress", "review", "normal", "limited", "not_connected"].includes(normalized) ? "status-warn"
        : ["resolved", "active", "live", "confirmed"].includes(normalized) ? ""
          : "status-muted";
    return `<span class="status-pill ${style}">${esc(String(value || "unknown").replaceAll("_", " "))}</span>`;
  }

  function table(headers, rows, emptyText = "No records found.") {
    return `<div class="table-wrap"><table class="data-table"><thead><tr>${headers.map((item) => `<th>${esc(item)}</th>`).join("")}</tr></thead><tbody>${rows.length ? rows.join("") : `<tr><td class="table-empty" colspan="${headers.length}">${esc(emptyText)}</td></tr>`}</tbody></table></div>`;
  }

  function cell(primary, secondary = "") {
    return `<span class="cell-primary">${esc(primary)}</span>${secondary ? `<span class="cell-secondary">${esc(secondary)}</span>` : ""}`;
  }

  async function renderPage() {
    const target = $("#page");
    target.innerHTML = `<div class="loading-state"><span class="spinner" aria-hidden="true"></span></div>`;
    renderNavigation();
    try {
      switch (state.page) {
        case "overview": target.innerHTML = await overviewPage(); break;
        case "users": target.innerHTML = await usersPage(); break;
        case "content": target.innerHTML = await contentPage(); break;
        case "payments": target.innerHTML = await paymentsPage(); break;
        case "notifications": target.innerHTML = await notificationsPage(); break;
        case "reports": target.innerHTML = await reportsPage(); break;
        case "roles": target.innerHTML = await rolesPage(); break;
        case "support": target.innerHTML = await supportPage(); break;
        case "audit": target.innerHTML = await auditPage(); break;
        case "configuration": target.innerHTML = await configurationPage(); break;
        case "sessions": target.innerHTML = await sessionsPage(); break;
        default: target.innerHTML = await limitedPage(state.page); break;
      }
      $("#updated-at").textContent = `Refreshed ${new Date().toLocaleTimeString()}`;
      wirePageActions(target);
    } catch (error) {
      target.innerHTML = `${heading(pageLabel(state.page), "The latest data could not be loaded.")}${notice(esc(error.message), "error")}<button id="retry-page" class="button" type="button">Try again</button>`;
      $("#retry-page")?.addEventListener("click", renderPage);
      if (error.message.includes("session has expired")) showLogin(error.message);
    }
  }

  function pageLabel(id) {
    return MODULES.find((item) => item.id === id)?.label || "Admin module";
  }

  async function overviewPage() {
    const [data, audit] = await Promise.all([
      api("/api/admin/overview"),
      permitted("audit") ? api("/api/admin/audit?page=1") : Promise.resolve({ events: [] }),
    ]);
    const metricCards = [
      ["Registered accounts", fmt(data.users), "Supabase Auth user directory"],
      ["Active · 30 days", data.active_users_30d === null ? "—" : fmt(data.active_users_30d), data.active_users_note || "Recent sign-ins"],
      ["Business workspaces", data.businesses === null ? "—" : fmt(data.businesses), "Saved business profiles"],
      ["Ledger entries", data.ledger_transactions === null ? "—" : fmt(data.ledger_transactions), "Business records · not platform revenue"],
    ];
    const events = (audit.events || []).slice(0, 5).map((item) => `<div class="activity-row"><span class="activity-marker"></span><span>${cell(item.action, `${item.actor_email} · ${date(item.created_at)}`)}</span></div>`);
    const pills = MODULES.map((item) => {
      const value = capability(item.id);
      return `<span class="module-pill ${value === "live" ? "" : "limited"}">${esc(item.label)}<em>${esc(capabilityText(value))}</em></span>`;
    }).join("");
    return `${heading("Your business, in the clear.", "A connected view of the CredEasy workspace. Admin actions are permission-checked and written to the activity trail.")}<section class="overview-hero"><div><p class="eyebrow hero-kicker">Operations snapshot</p><h2>Know what is happening.<br>See what still needs wiring.</h2><p>Account and product activity are shown separately. Ledger entries are business records, not CredEasy payment revenue.</p></div><div class="hero-motif" aria-hidden="true"><span class="hero-number">CE</span></div></section><section class="stat-grid">${metricCards.map(([label, value, detail]) => `<article class="stat-card"><span class="stat-label">${esc(label)}</span><strong class="stat-value">${esc(value)}</strong><span class="stat-detail">${esc(detail)}</span></article>`).join("")}</section><div class="data-grid">${panel("Recent admin activity", `<div class="panel-body"><div class="activity-list">${events.length ? events.join("") : `<span class="cell-secondary">No recent admin actions.</span>`}</div></div>`, "Latest auditable changes", permitted("audit") ? `<button class="button button-small" data-page-jump="audit">View log</button>` : "")}${panel("Module readiness", `<div class="panel-body"><div class="module-strip">${pills}</div></div>`, "Connected capabilities, not roadmap claims")}</div>`;
  }

  async function usersPage() {
    const query = state.search.trim();
    const data = await api(`/api/admin/users?page=${state.pageNumber}&search=${encodeURIComponent(query)}`);
    const manageAccess = state.admin.permissions.includes("user_access");
    const rows = (data.users || []).map((user) => {
      const suspended = !!user.banned_until && new Date(user.banned_until) > new Date();
      const isSelf = String(user.id) === String(state.admin.id);
      return `<tr><td>${cell(user.name || user.email || "Unknown", user.id)}</td><td>${esc(user.email || "—")}</td><td>${statusPill(user.email_confirmed ? "confirmed" : "unverified")}</td><td>${statusPill(suspended ? "suspended" : "active")}</td><td>${esc(shortDate(user.created_at))}</td><td><div class="heading-actions"><button class="button button-small" data-user-detail="${esc(user.id)}">View</button>${manageAccess ? `${user.email_confirmed ? "" : `<button class="button button-small" data-user-verify="${esc(user.id)}">Verify email</button>`}${isSelf ? "" : `<button class="button button-small ${suspended ? "" : "button-danger"}" data-user-suspend="${esc(user.id)}" data-suspended="${suspended}">${suspended ? "Restore" : "Suspend"}</button>`}<button class="button button-small" data-user-revoke="${esc(user.id)}">Revoke sessions</button>` : ""}</div></td></tr>`;
    });
    const actions = `<button id="search-users" class="button">Search accounts</button>`;
    return `${heading("User management", "Search the Supabase Auth directory, inspect linked business profiles, and manage account access.", actions)}${notice("Suspending blocks authentication through Supabase. Session revocation is global for the selected account and is recorded in the audit trail.")}${state.search ? `<p class="cell-secondary">Search applies to the loaded page of 50 users, not the complete directory.</p>` : ""}${panel("Accounts", table(["Account", "Email", "Verification", "Access", "Joined", "Actions"], rows, "No accounts on this page."), `${data.total === null ? "Directory results" : `${fmt(data.total)} total accounts`} · page ${data.page}` , `<div class="heading-actions"><button class="button button-small" data-user-page="${Math.max(1, state.pageNumber - 1)}">Previous</button><button class="button button-small" data-user-page="${state.pageNumber + 1}" ${rows.length < 50 ? "disabled" : ""}>Next</button></div>`)}`;
  }

  async function contentPage() {
    const data = await api("/api/admin/content");
    const rows = (data.items || []).map((item) => `<tr><td>${cell(item.title, item.id)}</td><td>${esc(item.content_type)}</td><td>${statusPill(item.status)}</td><td>${esc(date(item.updated_at))}</td><td><button class="button button-small" data-content-edit="${esc(item.id)}" data-title="${esc(item.title)}" data-type="${esc(item.content_type)}" data-status="${esc(item.status)}" data-body="${esc(item.body)}">Edit</button></td></tr>`);
    return `${heading("Content management", "Maintain centrally stored banners, categories, and announcements without implying they are already delivered to the app.", `<button class="button button-primary" id="new-content">＋ New content</button>`)}${notice(`<strong>Limited connection.</strong> ${esc(data.delivery)} Items can be saved as drafts or sent for review.`, "warning")}${panel("CMS items", table(["Title", "Type", "Status", "Last updated", "Actions"], rows), `${data.items.length} items`)}`;
  }

  async function paymentsPage() {
    const [transactions, bills] = await Promise.all([
      api(`/api/admin/ledger?kind=transactions&page=${state.pageNumber}`),
      api(`/api/admin/ledger?kind=bills&page=${state.pageNumber}`),
    ]);
    const transactionRows = (transactions.records || []).map((item) => `<tr><td>${cell(item.id, item.party_id || "No party")}</td><td>${esc(item.user_id || "—")}</td><td>${esc(item.type || "—")}</td><td>${esc(item.amount ?? "—")}</td><td>${esc(item.date || shortDate(item.created_at))}</td><td>${esc(item.note || "—")}</td></tr>`);
    const billRows = (bills.records || []).map((item) => `<tr><td>${cell(item.id, item.party_id || "No party")}</td><td>${esc(item.user_id || "—")}</td><td>${esc(item.total ?? "—")}</td><td>${statusPill(item.status || "recorded")}</td><td>${esc(date(item.created_at))}</td></tr>`);
    return `${heading("Payments & transactions", "Review the business transactions recorded in CredEasy. Payment processing and refunds are not connected.")}${notice(`<strong>Important:</strong> ${esc(transactions.note || "Ledger transactions are not processor payments. No refund, commission, or platform revenue data is inferred.")}`, "warning")}${panel("Ledger transactions", table(["Entry", "Account", "Type", "Amount", "Date", "Note"], transactionRows, "No transactions found."), "Latest 50 records")}${panel("Bills", table(["Bill", "Account", "Total", "Status", "Created"], billRows, "No bills found."), "Latest 50 bills")}`;
  }

  async function notificationsPage() {
    const data = await api("/api/admin/announcements");
    const rows = (data.items || []).map((item) => `<tr><td>${cell(item.title, item.id)}</td><td>${esc(item.audience)}</td><td>${statusPill(item.status)}</td><td>${esc(date(item.created_at))}</td><td>${esc(item.body)}</td></tr>`);
    return `${heading("Notifications", "Prepare an announcement for review. Sending and scheduled push delivery are not enabled.", `<button class="button button-primary" id="new-announcement">＋ Draft announcement</button>`)}${notice(`<strong>Drafts only.</strong> ${esc(data.delivery)} This page does not send a push or in-app notification.`, "warning")}${panel("Announcement drafts", table(["Title", "Audience", "State", "Created", "Message"], rows), `${data.items.length} drafts`)}`;
  }

  async function reportsPage() {
    const data = await api("/api/admin/reports");
    const reportRows = Object.entries(data.overview || {}).filter(([key]) => key !== "checked_at" && key !== "active_users_note").map(([key, value]) => `<tr><td>${esc(key.replaceAll("_", " "))}</td><td>${esc(value === null ? "Unavailable" : fmt(value))}</td><td>${esc(key === "ledger_transactions" ? "Business ledger activity, not platform revenue" : "Supabase account/workspace metric")}</td></tr>`);
    const userRows = (data.recent_users || []).map((user) => `<tr><td>${esc(user.email || "—")}</td><td>${esc(shortDate(user.created_at))}</td><td>${esc(date(user.last_sign_in_at))}</td></tr>`);
    return `${heading("Reports & exports", "Export current account and workspace indicators for operational reporting.")}${notice(esc(data.note), "warning")}<div class="heading-actions report-actions"><button class="button button-primary" id="export-overview">Export overview CSV</button><button class="button" id="export-users">Export account directory page CSV</button></div>${panel("Overview metrics", table(["Metric", "Value", "Interpretation"], reportRows), "Current connected data")}${panel("Accounts on first directory page", table(["Email", "Created", "Last sign-in"], userRows), `${userRows.length} accounts returned`)}`;
  }

  async function rolesPage() {
    const data = await api("/api/admin/roles");
    const owner = state.admin.role === "owner";
    const rows = (data.roles || []).map((item) => `<tr><td>${cell(item.email, item.user_id)}</td><td>${statusPill(item.role)}</td><td>${statusPill(item.active ? "active" : "suspended")}</td><td>${esc(date(item.created_at))}</td><td>${owner ? `<button class="button button-small button-danger" data-role-revoke="${esc(item.user_id)}">Revoke access</button>` : "—"}</td></tr>`);
    return `${heading("Roles & permissions", "Grant least-privilege staff roles and review who can enter the operations console.", owner ? `<button class="button button-primary" id="new-role">＋ Grant staff access</button>` : "")}${notice(owner ? "Only bootstrap owners can grant or revoke admin roles. A staff member must first have a verified CredEasy account; copy their account ID from User management." : "Your role is read-only for admin access management.")}${panel("Admin access", table(["Team member", "Role", "Access", "Added", "Actions"], rows), `${data.roles.length} role assignments`)}`;
  }

  async function supportPage() {
    const data = await api("/api/admin/tickets");
    const rows = (data.tickets || []).map((item) => `<tr><td>${cell(item.subject, item.id)}</td><td>${esc(item.requester_email)}</td><td>${statusPill(item.priority)}</td><td>${statusPill(item.status)}</td><td>${esc(date(item.updated_at))}</td><td><button class="button button-small" data-ticket-edit="${esc(item.id)}" data-status="${esc(item.status)}" data-priority="${esc(item.priority)}">Update</button></td></tr>`);
    return `${heading("Support tickets", "Track and resolve support requests in one place.", `<button class="button button-primary" id="new-ticket">＋ Log ticket</button>`)}${panel("Ticket queue", table(["Subject", "Requester", "Priority", "Status", "Updated", "Actions"], rows), `${data.tickets.length} tickets`)}`;
  }

  async function auditPage() {
    const data = await api(`/api/admin/audit?page=${state.pageNumber}`);
    const rows = (data.events || []).map((event) => `<tr><td>${esc(date(event.created_at))}</td><td>${cell(event.actor_email, event.actor_id)}</td><td>${statusPill(event.action)}</td><td>${esc(event.resource_type)}</td><td>${esc(event.resource_id || "—")}</td><td><button class="button button-small" data-audit-detail="${esc(event.id)}" data-details="${esc(JSON.stringify(event.details || {}))}">Details</button></td></tr>`);
    return `${heading("Audit history", "An append-only view of meaningful administrator actions.")}${panel("Admin activity", table(["When", "Actor", "Action", "Resource", "Resource ID", "Details"], rows, "No admin actions have been recorded."), `Page ${data.page}`, `<button class="button button-small" data-audit-page="${state.pageNumber + 1}">Older events</button>`)}`;
  }

  async function configurationPage() {
    const data = await api("/api/admin/configuration");
    const rows = (data.settings || []).map((item) => `<tr><td>${cell(item.key, item.updated_by)}</td><td><code>${esc(JSON.stringify(item.value))}</code></td><td>${esc(date(item.updated_at))}</td></tr>`);
    return `${heading("Feature configuration", "Keep proposed app settings in one auditable location.")}${notice(`<strong>Limited connection.</strong> ${esc(data.delivery)} Do not use stored values as active access controls until rollout is implemented.`, "warning")}${panel("Configuration values", table(["Key", "JSON value", "Last updated"], rows), `${data.settings.length} settings`, `<button class="button button-primary button-small" id="new-setting">＋ Add setting</button>`)}`;
  }

  async function sessionsPage() {
    const data = await api(`/api/admin/users?page=${state.pageNumber}&search=${encodeURIComponent(state.search)}`);
    const rows = (data.users || []).map((user) => `<tr><td>${cell(user.email || "—", user.id)}</td><td>${esc(date(user.last_sign_in_at))}</td><td>${esc(user.provider || "—")}</td><td><button class="button button-small" data-user-revoke="${esc(user.id)}">Revoke all sessions</button></td></tr>`);
    return `${heading("Sessions & devices", "Revoke all sessions for an account when access needs to be reset.")}${notice("Limited visibility: Supabase exposes account-level global revocation here, but this app does not record or list individual device sessions.", "warning")}${panel("Account access", table(["Account", "Last sign-in", "Provider", "Action"], rows), `Page ${data.page}` , `<button class="button button-small" data-user-page="${state.pageNumber + 1}" ${rows.length < 50 ? "disabled" : ""}>Next</button>`)}`;
  }

  async function limitedPage(id) {
    const labels = {
      orders: ["Orders & bookings", "CredEasy does not currently have a booking or order workflow connected to this console.", "not_connected"],
      coupons: ["Coupons & discounts", "Coupon records and discount application are not connected to the mobile app or a billing service.", "not_connected"],
      vendors: ["Vendors & partners", "A centralized vendor onboarding and payout workflow is not part of the current CredEasy product integration.", "not_connected"],
      moderation: ["Content moderation", "There is no user-generated public content moderation queue connected to this app.", "not_connected"],
      versions: ["App versions", "The mobile app does not currently check a centrally managed minimum version or force-update policy.", "not_connected"],
    };
    const [title, description, status] = labels[id] || ["Admin module", "This module is not connected.", "not_connected"];
    return `${heading(title, description)}<article class="capability-card"><h3>${esc(title)} integration</h3><p>${esc(description)} This screen intentionally does not offer pretend controls or create changes that are not consumed by the product.</p>${statusPill(capabilityText(status))}</article>`;
  }

  function csvCell(value) {
    return `"${String(value ?? "").replaceAll('"', '""')}"`;
  }

  function downloadCsv(name, headers, rows) {
    const content = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob(["\ufeff", content], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function openModal(title, inner, submitLabel, onSubmit) {
    const backdrop = document.createElement("div");
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `<section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header class="modal-header"><h2 id="modal-title">${esc(title)}</h2><button class="icon-button" type="button" aria-label="Close dialog" data-modal-close>×</button></header><div class="modal-body"><form id="modal-form" class="form-grid">${inner}<div class="form-actions"><button class="button" type="button" data-modal-close>Cancel</button><button class="button button-primary" type="submit">${esc(submitLabel)}</button></div></form></div></section>`;
    document.body.append(backdrop);
    const close = () => backdrop.remove();
    backdrop.querySelectorAll("[data-modal-close]").forEach((button) => button.addEventListener("click", close));
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) close();
    });
    backdrop.querySelector("form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = backdrop.querySelector('[type="submit"]');
      submit.disabled = true;
      try {
        await onSubmit(new FormData(event.currentTarget));
        close();
        await renderPage();
      } catch (error) {
        toast(error.message, true);
        submit.disabled = false;
      }
    });
    backdrop.querySelector("input, textarea, select")?.focus();
  }

  async function perform(path, method, payload, successMessage) {
    await api(path, { method, ...(payload ? { body: JSON.stringify(payload) } : {}) });
    toast(successMessage);
    await renderPage();
  }

  function wirePageActions(target) {
    target.querySelectorAll("[data-page-jump]").forEach((button) => button.addEventListener("click", () => {
      state.page = button.dataset.pageJump;
      renderPage();
    }));

    $("#search-users")?.addEventListener("click", () => {
      openModal("Search accounts", `<div class="field field-full"><label for="user-search">Name or email (loaded page only)</label><input id="user-search" name="search" maxlength="160" value="${esc(state.search)}"></div>`, "Search", async (form) => {
        state.search = form.get("search").trim();
        state.pageNumber = 1;
      });
    });
    target.querySelectorAll("[data-user-page]").forEach((button) => button.addEventListener("click", () => {
      state.pageNumber = Number(button.dataset.userPage);
      renderPage();
    }));
    target.querySelectorAll("[data-audit-page]").forEach((button) => button.addEventListener("click", () => {
      state.pageNumber = Number(button.dataset.auditPage);
      renderPage();
    }));
    target.querySelectorAll("[data-user-detail]").forEach((button) => button.addEventListener("click", async () => {
      try {
        const data = await api(`/api/admin/users/${encodeURIComponent(button.dataset.userDetail)}`);
        const user = data;
        openModal("Account details", `<dl class="detail-list field-full"><dt>Name</dt><dd>${esc(user.name || "—")}</dd><dt>Email</dt><dd>${esc(user.email)}</dd><dt>Account ID</dt><dd>${esc(user.id)}</dd><dt>Provider</dt><dd>${esc(user.provider || "—")}</dd><dt>Confirmed</dt><dd>${user.email_confirmed ? "Yes" : "No"}</dd><dt>Created</dt><dd>${esc(date(user.created_at))}</dd><dt>Last sign-in</dt><dd>${esc(date(user.last_sign_in_at))}</dd><dt>Business profiles</dt><dd>${esc((user.businesses || []).map((item) => item.name || item.id).join(", ") || "None linked")}</dd></dl>`, "Close", async () => {});
        const dialog = document.querySelector(".modal");
        dialog?.querySelector('button[type="submit"]')?.addEventListener("click", (event) => {
          event.preventDefault();
          dialog.closest(".modal-backdrop")?.remove();
        });
      } catch (error) {
        toast(error.message, true);
      }
    }));
    target.querySelectorAll("[data-user-suspend]").forEach((button) => button.addEventListener("click", async () => {
      const suspended = button.dataset.suspended === "true";
      const action = suspended ? "restore access to" : "suspend";
      if (!confirm(`Are you sure you want to ${action} this account?`)) return;
      try {
        await perform(`/api/admin/users/${encodeURIComponent(button.dataset.userSuspend)}/status`, "PATCH", { suspended: !suspended }, suspended ? "Account access restored." : "Account suspended.");
      } catch (error) {
        toast(error.message, true);
      }
    }));
    target.querySelectorAll("[data-user-verify]").forEach((button) => button.addEventListener("click", async () => {
      if (!confirm("Confirm this account's email address as verified? Only do this after an approved identity check.")) return;
      try {
        await perform(`/api/admin/users/${encodeURIComponent(button.dataset.userVerify)}/verification`, "PATCH", {}, "Account email marked verified.");
      } catch (error) {
        toast(error.message, true);
      }
    }));
    target.querySelectorAll("[data-user-revoke]").forEach((button) => button.addEventListener("click", async () => {
      if (!confirm("Revoke every active session for this account? The user will need to sign in again.")) return;
      try {
        await perform(`/api/admin/users/${encodeURIComponent(button.dataset.userRevoke)}/revoke-sessions`, "POST", {}, "All account sessions revoked.");
      } catch (error) {
        toast(error.message, true);
      }
    }));

    $("#new-content")?.addEventListener("click", () => contentModal());
    target.querySelectorAll("[data-content-edit]").forEach((button) => button.addEventListener("click", () => contentModal(button)));
    $("#new-announcement")?.addEventListener("click", () => openModal("Draft an announcement", `<div class="field field-full"><label for="announcement-title">Title</label><input id="announcement-title" name="title" maxlength="160" required></div><div class="field"><label for="announcement-audience">Audience</label><select id="announcement-audience" name="audience"><option value="all">All users</option><option value="active_30d">Active in last 30 days</option><option value="unverified">Unverified accounts</option></select></div><div class="field field-full"><label for="announcement-body">Message</label><textarea id="announcement-body" name="body" maxlength="4000" required></textarea></div>`, "Save draft", async (form) => {
      await api("/api/admin/announcements", { method: "POST", body: JSON.stringify({ title: form.get("title").trim(), audience: form.get("audience"), body: form.get("body").trim() }) });
      toast("Announcement saved as a draft. Nothing was sent.");
    }));

    $("#new-ticket")?.addEventListener("click", () => openModal("Log a support ticket", `<div class="field field-full"><label for="ticket-email">Requester email</label><input id="ticket-email" name="requester_email" type="email" maxlength="320" required></div><div class="field field-full"><label for="ticket-subject">Subject</label><input id="ticket-subject" name="subject" maxlength="200" required></div><div class="field"><label for="ticket-priority">Priority</label><select id="ticket-priority" name="priority"><option>low</option><option selected>normal</option><option>high</option><option>urgent</option></select></div><div class="field field-full"><label for="ticket-description">Description</label><textarea id="ticket-description" name="description" maxlength="4000"></textarea></div>`, "Create ticket", async (form) => {
      await api("/api/admin/tickets", { method: "POST", body: JSON.stringify({ requester_email: form.get("requester_email").trim(), subject: form.get("subject").trim(), priority: form.get("priority"), description: form.get("description").trim() }) });
      toast("Support ticket created.");
    }));
    target.querySelectorAll("[data-ticket-edit]").forEach((button) => button.addEventListener("click", () => openModal("Update support ticket", `<div class="field"><label for="ticket-status">Status</label><select id="ticket-status" name="status"><option ${button.dataset.status === "open" ? "selected" : ""}>open</option><option ${button.dataset.status === "in_progress" ? "selected" : ""}>in_progress</option><option ${button.dataset.status === "resolved" ? "selected" : ""}>resolved</option></select></div><div class="field"><label for="ticket-priority">Priority</label><select id="ticket-priority" name="priority"><option ${button.dataset.priority === "low" ? "selected" : ""}>low</option><option ${button.dataset.priority === "normal" ? "selected" : ""}>normal</option><option ${button.dataset.priority === "high" ? "selected" : ""}>high</option><option ${button.dataset.priority === "urgent" ? "selected" : ""}>urgent</option></select></div>`, "Save changes", async (form) => {
      await api(`/api/admin/tickets/${encodeURIComponent(button.dataset.ticketEdit)}`, { method: "PATCH", body: JSON.stringify({ status: form.get("status"), priority: form.get("priority") }) });
      toast("Support ticket updated.");
    })));

    $("#new-role")?.addEventListener("click", () => openModal("Grant staff access", `<div class="field field-full"><label for="role-user-id">CredEasy account UUID</label><input id="role-user-id" name="user_id" required pattern="[0-9a-fA-F-]{36}"></div><div class="field field-full"><label for="role-email">Verified account email</label><input id="role-email" name="email" type="email" maxlength="320" required></div><div class="field field-full"><label for="role-name">Role</label><select id="role-name" name="role"><option value="support">Support · user + ticket access</option><option value="analyst">Analyst · analytics + finance read</option><option value="content">Content · CMS + configuration</option><option value="finance">Finance · ledger read-only</option><option value="admin">Admin · operational access (not role management)</option></select></div>`, "Grant access", async (form) => {
      await api("/api/admin/roles", { method: "POST", body: JSON.stringify({ user_id: form.get("user_id").trim(), email: form.get("email").trim(), role: form.get("role") }) });
      toast("Admin access granted.");
    }));
    target.querySelectorAll("[data-role-revoke]").forEach((button) => button.addEventListener("click", async () => {
      if (!confirm("Revoke this staff member's admin access?")) return;
      try {
        await perform(`/api/admin/roles/${encodeURIComponent(button.dataset.roleRevoke)}`, "DELETE", null, "Admin access revoked.");
      } catch (error) {
        toast(error.message, true);
      }
    }));

    $("#new-setting")?.addEventListener("click", () => openModal("Save configuration value", `<div class="field field-full"><label for="setting-key">Key</label><input id="setting-key" name="key" maxlength="80" pattern="[a-z][a-z0-9_.-]{1,79}" placeholder="feature.example_enabled" required></div><div class="field field-full"><label for="setting-value">JSON value</label><textarea id="setting-value" name="value" placeholder='true, 42, "text", or {"enabled":true}' required></textarea></div>`, "Save setting", async (form) => {
      let value;
      try {
        value = JSON.parse(form.get("value"));
      } catch {
        throw new Error("Enter a valid JSON value.");
      }
      await api("/api/admin/configuration", { method: "PUT", body: JSON.stringify({ key: form.get("key").trim(), value }) });
      toast("Configuration saved and audited. It is not yet consumed by the app.");
    }));

    target.querySelectorAll("[data-audit-detail]").forEach((button) => button.addEventListener("click", () => {
      let details;
      try {
        details = JSON.parse(button.dataset.details);
      } catch {
        details = {};
      }
      const serialized = JSON.stringify(details, null, 2);
      openModal("Audit event details", `<div class="field field-full"><label for="audit-json">Recorded fields</label><textarea id="audit-json" readonly>${esc(serialized)}</textarea></div>`, "Close", async () => {});
      const dialog = document.querySelector(".modal");
      dialog?.querySelector('button[type="submit"]')?.addEventListener("click", (event) => {
        event.preventDefault();
        dialog.closest(".modal-backdrop")?.remove();
      });
    }));

    $("#export-overview")?.addEventListener("click", () => {
      const values = $("#page .stat-card");
      downloadCsv("credeasy-admin-overview.csv", ["Metric", "Value", "Description"], [...values].map((item) => [
        item.querySelector(".stat-label").textContent,
        item.querySelector(".stat-value").textContent,
        item.querySelector(".stat-detail").textContent,
      ]));
    });
    $("#export-users")?.addEventListener("click", async () => {
      try {
        const data = await api("/api/admin/users?page=1&search=");
        downloadCsv("credeasy-recent-users.csv", ["ID", "Email", "Name", "Created at", "Last sign-in", "Email confirmed", "Status"], (data.users || []).map((user) => [
          user.id, user.email, user.name, user.created_at, user.last_sign_in_at, user.email_confirmed ? "Yes" : "No", user.banned_until ? "Suspended" : "Active",
        ]));
      } catch (error) {
        toast(error.message, true);
      }
    });
  }

  function contentModal(button) {
    const item = button?.dataset || {};
    openModal(button ? "Edit CMS content" : "Create CMS content", `<div class="field field-full"><label for="content-title">Title</label><input id="content-title" name="title" maxlength="160" value="${esc(item.title || "")}" required></div><div class="field"><label for="content-type">Type</label><select id="content-type" name="content_type"><option value="banner" ${item.type === "banner" ? "selected" : ""}>Banner</option><option value="category" ${item.type === "category" ? "selected" : ""}>Category</option><option value="announcement" ${item.type === "announcement" ? "selected" : ""}>Announcement</option></select></div><div class="field"><label for="content-status">Status</label><select id="content-status" name="status"><option value="draft" ${item.status !== "review" ? "selected" : ""}>Draft</option><option value="review" ${item.status === "review" ? "selected" : ""}>Needs review</option></select></div><div class="field field-full"><label for="content-body">Content / body</label><textarea id="content-body" name="body" maxlength="4000">${esc(item.body || "")}</textarea></div>`, button ? "Save changes" : "Save draft", async (form) => {
      const payload = { title: form.get("title").trim(), content_type: form.get("content_type"), status: form.get("status"), body: form.get("body").trim() };
      const endpoint = button ? `/api/admin/content/${encodeURIComponent(item.contentEdit)}` : "/api/admin/content";
      await api(endpoint, { method: button ? "PATCH" : "POST", body: JSON.stringify(payload) });
      toast(button ? "CMS content updated." : "CMS content saved.");
    });
  }

  async function initialize() {
    $("#google-login").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      if (!state.client) {
        $("#login-error").hidden = false;
        $("#login-error").textContent = "Admin sign-in is not configured. Contact your backend administrator.";
        return;
      }
      button.disabled = true;
      button.textContent = "Opening Google sign-in…";
      try {
        const { error } = await state.client.auth.signInWithOAuth({
          provider: "google",
          options: { redirectTo: `${window.location.origin}/admin`, scopes: "openid email profile" },
        });
        if (error) throw error;
      } catch (error) {
        $("#login-error").hidden = false;
        $("#login-error").textContent = error.message || "Google sign-in could not start.";
        button.disabled = false;
        button.textContent = "Continue with Google";
      }
    });
    $("#sign-out").addEventListener("click", async () => {
      try {
        await state.client.auth.signOut();
        state.session = null;
        state.admin = null;
        state.page = "overview";
        showLogin();
      } catch (error) {
        toast(`Could not safely sign out: ${error.message}`, true);
      }
    });
    $("#menu-toggle").addEventListener("click", () => $("#sidebar").classList.toggle("sidebar-open"));
    $("#app").hidden = true;
    $("#login").hidden = true;
    try {
      const configResponse = await fetch("/api/admin/config", { cache: "no-store" });
      const configText = await configResponse.text();
      let config;
      try {
        config = JSON.parse(configText);
      } catch {
        if (configResponse.status === 404) {
          throw new Error("The configured admin backend returned 404. Check the HTTPS backend URL in WordPress Settings → General and confirm the FastAPI admin routes are deployed.");
        }
        throw new Error("The admin backend returned an unreadable response. Check that the configured URL points to the CredEasy FastAPI service.");
      }
      if (!configResponse.ok) throw new Error(config.detail || `Admin sign-in configuration failed (${configResponse.status}).`);
      if (!window.supabase?.createClient) throw new Error("The local sign-in client did not load. Refresh the page or check the admin static files.");
      state.client = window.supabase.createClient(config.supabase_url, config.supabase_anon_key, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storage: window.sessionStorage },
      });
      state.client.auth.onAuthStateChange((_event, session) => {
        state.session = session;
      });
      const { data } = await state.client.auth.getSession();
      state.session = data.session;
      if (state.session) {
        try {
          state.admin = await api("/api/admin/me");
          await loadCapabilities();
          showApp();
          await renderPage();
          return;
        } catch (error) {
          await state.client.auth.signOut();
          state.session = null;
          showLogin(error.message);
          return;
        }
      }
      showLogin();
    } catch (error) {
      showLogin(error.message);
    }

  }

  initialize();
})();
