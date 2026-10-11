# Enable account deletion on the Android API

The Android app's configured API is the Cloud Run service
`credeasy-api-634736672458.asia-south1.run.app` in `asia-south1`. Account
deletion calls `DELETE /api/auth/account`; the backend intentionally returns
HTTP 503 and preserves local data unless `SUPABASE_SERVICE_ROLE_KEY` is
available to that service.

## Configure the key

1. In Google Cloud Console, open **Secret Manager** in the same project as the
   Cloud Run service. Create a secret such as `supabase-service-role-key` and
   add the service-role key for the Supabase project identified by the
   backend's `SUPABASE_URL`. Enter it directly in the secure console; do not
   paste it into chat, source files, or a client `.env`.
2. Open **Cloud Run → credeasy-api** in region `asia-south1` and note the
   service's runtime service account.
3. In Secret Manager, grant that service account **Secret Manager Secret
   Accessor** on this secret only.
4. Edit and deploy a new revision of `credeasy-api`. Under **Variables &
   Secrets**, add an environment variable named exactly
   `SUPABASE_SERVICE_ROLE_KEY`, sourced from an enabled, numbered secret
   version. Pin the version rather than using `latest` so each revision starts
   with the explicitly selected credential. Keep the existing `SUPABASE_URL`
   and `SUPABASE_ANON_KEY` configuration unchanged.
5. Wait for the new revision to become ready. Verify
   `https://credeasy-api-634736672458.asia-south1.run.app/api/health` returns
   `{"status":"ok"}`, then retry **Settings → Delete account** in the Android
   app and confirm the Security PIN.

The mobile app must never contain the service-role key. Failed remote deletion
must leave local data intact; do not clear it manually as part of setup.

## Deploy backend updates with Cloud Build

The repository includes `backend/Dockerfile` and a root-level
`cloudbuild.yaml`. The trigger builds only the backend directory, pushes an
image tagged with the unique Cloud Build ID to Artifact Registry, and updates
the existing `credeasy-api` service.
The backend Docker context excludes `.env` files; provider and Supabase secrets
must remain configured on the Cloud Run runtime service.

Before creating a trigger:

1. Create a Docker Artifact Registry repository named
   `credeasy-api-images` in `asia-south1`.
2. In **Cloud Build → Settings**, identify the build service account. Grant it
   **Artifact Registry Writer** and **Cloud Run Admin** in the project.
3. Grant that build service account **Service Account User** on the runtime
   service account used by `credeasy-api`. Keep **Secret Manager Secret
   Accessor** granted to the runtime service account, not just the build
   service account.
4. Push `backend/Dockerfile`, `backend/.dockerignore`, `cloudbuild.yaml`, and
   the backend source changes to the repository branch that the trigger will
   watch.
5. Create a Cloud Build trigger in `asia-south1` for **Push to a branch**.
   Select the connected CredEasy repository, enter the exact branch regex
   (for example, `^main$`), select the repository Cloud Build configuration,
   and set the config path to `cloudbuild.yaml`.
6. Run the trigger and wait for its build and deploy steps to succeed. In
   **Cloud Run → credeasy-api → Revisions**, verify the new revision is ready
   and receiving traffic. Confirm its runtime service account and Secret
   Manager bindings are still correct.

The deployment updates the container image of the existing service; it does
not set or expose secret values. Confirm the service still has
`SUPABASE_SERVICE_ROLE_KEY` and `GEMINI_API_KEY` configured from Secret
Manager. As of 2026-10-09, the active Cloud Run revision pins
`SUPABASE_SERVICE_ROLE_KEY` to version `1` of `supabase-service-role-key`.
After key rotation, pin the new enabled version and deploy a fresh revision.
Chotu currently uses Vertex AI with
`GEMINI_MODEL=gemini-2.5-flash-lite` and
`VERTEX_AI_LOCATION=us-central1`; Google lists this model for retirement on
October 20, 2026 ([model lifecycle](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions)),
so migrate to a supported replacement before that date. A successful
`/api/health` check does not validate either provider integration.

Chotu's Vertex AI setup is separate from the AI Studio Gemini API key:
`GEMINI_PROVIDER=vertex`, `GOOGLE_CLOUD_PROJECT=first-site-506918-r5`, and
`VERTEX_AI_LOCATION=us-central1` configure the Gemini 2.5 Flash-Lite regional
endpoint. Grant `roles/aiplatform.user` to the Cloud Run runtime service
account. The existing `GEMINI_API_KEY` secret can remain bound during
migration; it is not used while `GEMINI_PROVIDER=vertex`.

If Supabase Auth returns an error during account deletion, the backend logs its
error code, a bounded and redacted error message, and the Supabase request ID
when supplied. Use those fields in Cloud Run Logs Explorer to diagnose an
upstream HTTP 500; the client does not receive internal Supabase details.

### Fix the tombstone foreign-key failure

The deployed service logged Supabase error `23503` on
`party_deletions_user_id_fkey`. The sync setup's delete triggers were trying to
create party/transaction/bill/recurring/inventory tombstones while Supabase
Auth was cascading deletion of the owning user, so those new tombstones failed
their foreign key back to `auth.users`.

The updated `docs/enable-transaction-realtime.sql` keeps tombstones for direct
record deletes but skips them during nested foreign-key cascade deletes. In
the Supabase SQL Editor for the same project used by the app, rerun the entire
updated `enable-transaction-realtime.sql` setup script. It is designed to be
safe to rerun and updates the trigger functions in place. Do not run
`docs/supabase-migration.sql`; that separate migration drops tables. After the
updated setup completes, retry account deletion from the app only if deletion
is still intended. This fix is a Supabase SQL change; it does not require a
new Android APK or Cloud Run deployment.
