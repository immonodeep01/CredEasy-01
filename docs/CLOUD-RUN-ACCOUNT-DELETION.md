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
   `SUPABASE_SERVICE_ROLE_KEY`, sourced from the secret and its latest enabled
   version. Keep the existing `SUPABASE_URL` and `SUPABASE_ANON_KEY`
   configuration unchanged.
5. Wait for the new revision to become ready. Verify
   `https://credeasy-api-634736672458.asia-south1.run.app/api/health` returns
   `{"status":"ok"}`, then retry **Settings → Delete account** in the Android
   app and confirm the Security PIN.

The mobile app must never contain the service-role key. Failed remote deletion
must leave local data intact; do not clear it manually as part of setup.
