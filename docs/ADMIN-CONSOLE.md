# CredEasy Admin Console

The internal operations console is served by the existing FastAPI backend at
`/admin`. It uses the existing Supabase Google sign-in, the verified session
for each request, server-side role checks, and a backend-only Supabase service
role key for administrative reads and writes.

## Enable the console

1. Apply [`enable-admin-panel.sql`](./enable-admin-panel.sql) in the Supabase
   SQL editor. The script adds private admin data tables and creates no
   `anon` or `authenticated` RLS policies.
2. Configure the backend with `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY`, and `ADMIN_BOOTSTRAP_EMAILS`. Set the bootstrap
   variable to a comma-separated allowlist of verified Google account emails.
   Keep the service role key in the backend's secret store only; it is never
   sent to the browser.
3. In Supabase Auth, enable Google sign-in and allow the deployed backend's
   exact `/admin` URL as a redirect URL. The admin client requests only
   `openid email profile`; it does not request Google Drive access.
4. Deploy/restart the backend and open `https://<backend-host>/admin`. Sign in
   with an allowlisted owner account. Use the User management page to copy an
   existing account UUID, then grant staff a least-privilege role from Roles &
   permissions.
5. Remove departed bootstrap owners from `ADMIN_BOOTSTRAP_EMAILS`, and review
   staff roles and the audit log regularly.

If the SQL migration is not installed or the service role key is missing, the
console reports a configuration error rather than presenting empty data as a
successful connection.

## Module connection boundaries

- **Connected:** Google-authenticated account listing, verification state,
  owner/admin-reviewed email verification, account suspension/restoration,
  global session revocation, staff roles,
  activity/audit log, support ticket tracking, read-only business transactions
  and bills, connected account/workspace metrics, and CSV exports.
- **Limited/draft only:** CMS content is stored for review but the mobile app
  does not consume it; announcements are drafts only and are not delivered;
  app configuration is stored but not yet read by the app; session management
  revokes every session for an account but does not list individual devices.
- **Not connected:** payment processor/refunds/commissions, orders/bookings,
  coupon redemption, vendor onboarding/payouts, public-content moderation,
  and minimum-version enforcement. The console identifies these gaps and does
  not expose controls that would falsely imply those actions work.

Ledger transaction totals represent user business activity; they are not
CredEasy platform revenue. The console does not infer revenue or commissions.

## Validation

Run the targeted admin security and integration tests from the repository
root:

```powershell
python -m pytest backend\tests\test_admin_console.py -q
```

Run the full backend test suite before deploying backend changes:

```powershell
python -m pytest backend\tests -q
```
