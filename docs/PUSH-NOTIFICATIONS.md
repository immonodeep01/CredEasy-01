# Push notifications

CredEasy supports Android push messages for opted-in devices, plus private
device-local reminders derived from ledger and inventory state. The Settings
switch is explicit opt-in. Lock-screen reminder text is generic and does not
include a party name or amount.

## Provider setup

1. In Firebase, register an Android app with package name
   `com.credeasy.app`, enable Firebase Cloud Messaging, and download its
   `google-services.json`.
2. Put that file at `frontend/google-services.json`. It is gitignored; do not
   commit it or paste its contents into chat. `frontend/app.config.js` adds it
   to the Android Expo config when the local file exists. For remote EAS
   builds, configure `GOOGLE_SERVICES_JSON` as a file-type EAS environment
   variable so the build worker can access the Firebase config.
3. In the EAS project `immonos-team/credeasy`, add an FCM V1 service-account
   credential using the Firebase project's service account. Use the
   interactive `eas credentials -p android` flow locally. Do not send the
   private key through chat or commit it.
4. Create an Expo access token and add it to the Cloud Run service as the
   `EXPO_ACCESS_TOKEN` secret. Push delivery fails closed until this secret is
   configured. The backend uses it only when calling Expo's push service; it
   is never sent to the app.
5. Build and install a new Android release after adding the Firebase file and
   EAS FCM credential. For a local Gradle build, run
   `npx expo prebuild --platform android` first so Expo applies the Google
   Services plugin and copies the Firebase config into the native project; a
   direct Gradle build does not apply Expo config plugins. A previously
   installed binary cannot gain the native Firebase configuration.

The backend service also needs the already-configured `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, and user-auth verification settings. The
service-role key remains backend-only.

## Database and backend

1. Apply [`enable-push-notifications.sql`](./enable-push-notifications.sql) in
   the Supabase SQL editor after [`enable-admin-panel.sql`](./enable-admin-panel.sql).
   It creates a private Android device-token table and extends the existing
   announcement history table for targeted delivery state.
2. Deploy the backend changes. The app registers and removes its own token
   through authenticated endpoints; the backend derives the account ID from
   the verified session. Admin send actions require existing server-side
   content permission and are audited.
3. Open the Android app, sign in, then enable **Settings → Preferences → Push
   notifications** and allow Android's notification permission. Offline-only
   mode keeps the device-local ledger reminders but does not register a
   remote-push token.

## Sending from the admin console

- Draft an announcement, then choose **Send now** to broadcast it to all
  registered, opted-in Android devices.
- Choose **Send to one account** and enter the account UUID shown in User
  management to send a private message to that account's registered devices.
- Both actions send immediately; scheduled delivery is not implemented.
  Provider acceptance is recorded separately from device delivery.
- Keep push copy free of customer names, balances, and other sensitive ledger
  details because the operating system may display it on the lock screen.

## Ledger reminders and limits

After opt-in, a newly appearing overdue customer balance or low-stock condition
creates one generic local notification for that event on the device. Existing
conditions are baselined when notifications are first enabled, and clearing a
condition before it returns prevents duplicate alerts. The app checks ledger
state when Ledger or Inventory refreshes; there is no server scheduler, so
these reminders are not guaranteed while the app is inactive or before the
device refreshes synced data.

## Validation

Run the focused backend tests:

```powershell
python -m pytest backend\tests\test_admin_console.py -q
```

After database setup and deployment, use a signed-in Android release build to
opt in, verify one `push_devices` row for the account, and send a test message
from `/admin`. Confirm the notification opens the in-app notification list.
