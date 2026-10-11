# CredEasy launch-scale audit

## Scope and verification

This is a source-code audit for the requested 10,000-user launch target. The
repository's schema is not the schema named in the checklist: CredEasy uses
`parties`, `transactions`, `bills`, and business workspaces. It has no
`ledger_accounts`, `business_users`, `reminder_logs`, `voice_sessions`,
`subscriptions`, `account_id`, or Supabase Edge Functions.

Source-level changes are covered by the backend auth/voice tests, frontend
TypeScript, and focused ESLint. No staging Supabase URL or test credentials
were available. Do not substitute production traffic: live RLS
`EXPLAIN ANALYZE` and the 10,000-user load test were not run, and no p95 latency
is claimed.

## Findings

| # | Area | Finding and action |
|---|---|---|
| 1 | Indexes | The additive sync migration creates unique `(user_id, business_id, id)` indexes for `transactions`, `bills`, and other synced tables. Base schema indexes include `transactions.party_id`, `bills.party_id`, and user ownership columns. There is no `account_id`; the equivalent transaction-to-party key is `party_id`. Transaction IDs are primary keys and writes use upsert, so the requested `add_transaction()` lookup does not exist; its equivalent conflict path uses the primary-key index. There is no `business_users` policy subquery. Index definitions were source-reviewed, not checked against a live catalog or query plan. |
| 2 | Pagination | Cloud ledger/inventory pulls now read ordered `.range()` pages capped at 500 rows. The business-profile directory also uses bounded 500-row pages. Legacy parties and transactions endpoints enforce pages of at most 50 rows and return offset metadata. Admin users, ledger, audit, roles, CMS content, announcements, support tickets, configuration, and report account tables use offset pages capped at 50, with matching controls in the console. Single-row lookups use `.maybeSingle()` or `.limit(1)`. |
| 3 | Connection pooling | Mobile and backend use Supabase Auth/REST/Storage HTTP APIs; the repository contains no direct PostgreSQL driver or `DATABASE_URL` path and no Edge Functions. Therefore application connections do not scale one-to-one with users as direct PostgreSQL sessions. Core API and ledger-write paths reuse the backend's shared HTTPX client (100 connections, 20 keep-alive); low-volume admin and optional import-auth helpers still use short-lived HTTPX clients, not direct database sessions. The hosted Supabase pooler mode cannot be independently verified from this checkout. |
| 4 | N+1 queries | Home and ledger balances are computed from the local ledger snapshot; the reviewed Home, business-switcher, and balance paths do not issue one Supabase query per account. No batch-query change was needed. |
| 5 | RLS performance | Current ledger policies check `auth.uid() = user_id`; they do not contain the requested `business_users` membership subquery. Ownership indexes exist in the base schema and composite user/business indexes in the additive migration. Live `EXPLAIN ANALYZE` remains unverified without staging database access. |
| 6 | Background jobs | No nightly reconciliation or reminder-scan cron job, `pg_cron` schedule, or equivalent worker exists in this repository. There is nothing to batch or change. |
| 7 | Voice cost controls | Added a shared authenticated-account quota of 20 voice requests per 60-second fixed window using `consume_voice_request_limit()` in the additive SQL migration, alongside the local early-rejection limit. This owner-wide quota also caps each current workspace and is stricter when one account has multiple workspaces. Added per-provider circuit breaking after repeated failures; the circuit is process-local, with a 30-second cooldown and one half-open probe, not a fleet-wide breaker. Apply the SQL migration before deploying the updated backend. |
| 8 | Storage | Existing client and bucket limits cap media at 5 MiB. Cloud-bound photos/logos are now resized to a 1600-pixel maximum edge and JPEG-compressed before upload; PNG transparency is preserved. The final encoded size is checked before upload, and an image still over 5 MiB fails visibly. |
| 9 | Observability | Backend logs API 5xx/unhandled failures and requests taking at least two seconds, without transcript or ledger content. Existing voice provider timing logs remain. Configure Cloud Logging alerts for `API request failed` and `Slow API request`; hosted Supabase database slow-query alerts still require project-console access. |
| 10 | Load test | **Blocked, not run.** No staging endpoint or test credentials were supplied, and production was not used as a substitute. The actual p95 for auth, transaction writes, and voice is therefore unavailable; it must be measured against staging before treating the 10,000-user target as load-verified. |

## Validation

- `backend/tests/test_auth.py`: 44 passed.
- Frontend `tsc --noEmit`: passed.
- Focused ESLint for the modified sync and image-storage modules: passed.
- Live SQL migration execution, RLS query-plan inspection, Cloud Logging alert
  configuration, and staging load test: not performed.
