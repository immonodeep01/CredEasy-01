# CredEasy - Project Context

## Project Overview
A mobile-first business ledger app (React Native + Expo) with Supabase backend, voice assistant, Google Drive backup, and ads (AdMob). Offline-first architecture where Supabase cloud sync has known issues.

The internal operations console is served by the FastAPI backend at `/admin`; it uses Google OAuth, server-side admin roles and the backend-only Supabase service key. Apply `docs/enable-admin-panel.sql` and configure `ADMIN_BOOTSTRAP_EMAILS` before use; never expose `SUPABASE_SERVICE_ROLE_KEY` to the browser. The console documents CMS/push/config/session limitations and does not pretend disconnected payments, orders, coupons, vendors, moderation, or version enforcement are live. See `docs/ADMIN-CONSOLE.md`.
The Managed WordPress theme package also serves its bundled admin UI at `/admin` and proxies a strict allowlist of `/api/admin/*` routes to the FastAPI backend; route parsing works without a rewrite flush, and its static JS/CSS load directly from the active theme directory. Configure the API origin (`https://credeasy-01.onrender.com`, not the static website host) under **WordPress Settings → General → CredEasy Admin** (also linked under Settings → CredEasy Admin; no `wp-config.php` or SFTP edit is needed), and verify `<backend-origin>/api/admin/config` returns JSON before adding it. The current API deployment must first be updated to include `backend/admin_console.py`; currently `/api/admin/config` returns 404 although `/api/health` works. Allow the exact WordPress `/admin` OAuth redirect in Supabase. Existing installs on v1.3.0 can refresh rewrite rules under **Settings → Permalinks → Save Changes**. Rebuild `credeasy-wordpress-theme.zip` with `python website/build-wordpress-theme.py`; see `docs/WEBSITE-GODADDY-DEPLOYMENT.md`.

The Parties/contact list has a header search toggle that reveals a name-or-phone filter; closing search clears the active query.

Chotu is CredEasy's friendly in-app voice helper. Keep its structured JSON replies warm, concise, language-matched, and conversational; it can teach users the app, answer ledger/inventory questions, navigate to supported screens, and propose ledger or stock changes. Never execute model-generated transaction or stock changes without a separate user confirmation; frame changes as proposals and delimit business context as untrusted input. The backend uses Gemini 2.5 Flash-Lite for assistant replies, Google Cloud Speech-to-Text v2 for transcription, and Google Cloud Text-to-Speech for speech when configured with a project and backend Application Default Credentials. Native STT uses `chirp_3` streaming with adaptive client-side VAD and short PCM preroll, with same-provider audio-upload fallback if the WebSocket cannot connect; web keeps the upload pipeline. Google TTS uses male Indian `hi-IN-Chirp3-HD-Puck` for Hindi and `en-IN-Chirp3-HD-Puck` for Indian English; infer Hindi from Devanagari replies even when the app UI language is English. TTS response headers identify the actual provider and voice for diagnosis. Deploy the backend and configure Google Cloud before expecting these voice changes; the deployed API must include the streaming route to provide interim transcripts instead of WAV-upload fallback. Never put provider credentials in the mobile app. After the user explicitly starts a mic session, adaptive VAD pauses and submits speech automatically; microphone capture stays stopped during spoken replies and resumes after playback finishes. Native cleanup must not poll or call Expo's file recorder after capture stops. Preserve legacy speech fallback only when Google Cloud is unconfigured; never switch providers after a configured Google or Gemini provider fails, and do not send ledger context to a different provider.
Android packaging must stage the ABI-matched Oboe shared libraries from the resolved Prefab artifact into the app JNI library source set; verify `liboboe.so` is present beside `libreact-native-audio-api.so` in release APKs.
The Expo file recorder is mounted only on web; native Chotu uses PCM capture, keeps the session listening after silence, and cancels active capture when typed input is submitted. Adaptive VAD uses a 0.0025 minimum speech-onset RMS with multi-frame gating for quiet speech, and the shared backend TTS endpoint converts rupee figures such as ₹66,254 to spoken number words; deploy backend changes for production pronunciation updates. The Chotu widget setup screen must recheck microphone and notification grants on route focus and app resume, showing the placement steps rather than another permission call when access is already granted.
The Android home-screen Chotu widget is implemented with `react-native-android-widget` headless tasks, shared assistant/context/STT/TTS helpers, and a microphone foreground service. It has a single idle microphone on the right; while listening, Stop is left of Send, and speech is submitted only on Send. Transaction and stock changes are confirmed by saying yes/no through the mic; adding a party is not allowed from the widget. `NAVIGATE` and `REMIND` explain their app/share-screen dependency without launching CredEasy. Keep `frontend/patches/react-native-android-widget+0.22.1.patch` because the headless worker's default 30-second deadline is too short for speech and assistant turns. Its compact states use only the library's widget primitives and CredEasy light/dark tokens. Size its launcher footprint to about four app icons across and one row high, and use the current CredEasy app mark rather than the Chotu character for widget artwork. Native speech capture uses lower bounded adaptive thresholds and multi-frame onset/release gating so quiet speech is detected without intermittent background noise keeping the turn open. The backend speaks explicitly marked rupee amounts and grouped numbers as Indian number words through the shared TTS endpoint. Run the settings permission setup before use; Expo Go is unsupported. In the in-app voice party-creation flow, request Contacts access only after an explicit add-party request; transaction entry must not request it. See `docs/CHOTU-WIDGET.md` for build/test steps.
Carry Google Speech-to-Text's detected locale through the voice turn so Hindi speech receives a Hindi reply voice even when the app interface is set to English. Use the Hindi/English Chirp 3 HD `Puck` male voices; do not send unverified phrase-set adaptation to Chirp 3.
The Ledger dock is a transparent overlay above the bottom bar, with Chotu on the left and Add customer on the right, so party names remain visible behind the motion lane; reserve only scrollable tail space so the final party can scroll clear of the controls. Use the idle, wave, running, walking, story, sleepy, reaction, and thinking sequences from the supplied LittleI spritesheet, cropped to `frontend/assets/images/chotu-sheet-*`; keep the existing jumping pose and show only one pose visible at a time. Select actions and 5–6 second idle holds randomly; each run travels between the dock edges, with facing determined by the individual run sprite's native direction and reversed for the return run. Say a localized “Hi” and wave immediately at the left dock on every Ledger focus, without retriggering when the keyboard or business picker changes mascot visibility. After the greeting, start the first run 7–8 seconds later at half the prior speed, with repeated run-cycle frames for visible footsteps. Sometimes replace the wave greeting with 5–6 jumps and repeated localized “Hi!” text. Keep the bubble anchored above the left side so it never follows him. Hold the seated/story pose for 5–6 seconds. Use reduced-motion-aware Reanimated and keep Chotu low, immediately above the bottom bar, with the ground shadow staying on the track while he runs or jumps. On the login screen, scale the logo artwork to fill its clipped badge and avoid a visible white inset; retain other logo sizes elsewhere. The login green hero uses a compact horizontal CredEasy lockup and a left-aligned supporting statement. The Preferences setting `Chotu mascot` persists its visibility; when off, right-align the single up-chevron action that opens Add customer and voice-assistant mic shortcuts. Hide the dock for the keyboard and business chooser, and route Chotu taps to the existing voice-assistant sheet without auto-starting recording.
The account-scope and required-access startup gates use the branded `AppLoadingPanel` instead of an unlabelled activity spinner; preserve the underlying route and access checks. The initial `SplashScreen` follows the active light/dark CredEasy palette. The More tab uses an up-chevron to signal its upward-opening menu.

For native voice playback, convert the fetch response Blob to base64 with `FileReader.readAsDataURL`; React Native's Blob does not implement `arrayBuffer()`. The backend returns Google Cloud Text-to-Speech MP3 bytes.

Settings links to the Google Drive Backup screen for backup status and Drive backup/restore actions; the removed manual JSON backup/restore controls remain removed.
The in-app notification list is generated from the local ledger and persisted in `src/utils/notification-store.ts`; preserve read state by notification ID, derive Home/native badge counts from that list, and clear both when imported data replaces the ledger. Scheduled local follow-up helpers currently have no UI call site.
Onboarding previous-data import accepts CSV files only; the file picker validates `.csv` because Android document providers report inconsistent MIME types. Parse locally, scan past export metadata, support CredEasy's compacted multi-table CSV rows, and show every parsed row for review. Do not send ledger documents to external AI services. OkCredit backup-summary CSVs contain party balances but no transaction history; parse their fused/packed Due and Advance columns into signed opening balances.

The bottom navigation has three direct tabs—Ledger, Inventory and Billing—and an up-arrow More menu containing Reports, Profile, Help & Support, and Settings; Parties remains a hidden route. Settings contains only Preferences, Google Account Login, and Google Drive Backup; it does not expose account deletion. Profile stores business name, phone, GSTIN, business type, category, address and email alongside the existing UPI and QR payment details. Inventory records keep optional SKU, barcode, HSN/SAC, GST, category, cost, location and tax-inclusive metadata. Inventory items and movements persist locally first and sync through durable outboxes and Supabase Realtime when authenticated; movement deltas are applied server-side against the current cloud stock to avoid stale-device overwrites. Item deletion uses tombstones, movement history remains after item deletion, and Drive backups include inventory data. Run the additive `docs/enable-transaction-realtime.sql` setup in Supabase before expecting cross-device sync for ledger, bills, recurring transactions, profiles or inventory.
Each Google account can own multiple business workspaces. Keep a stable business UUID on each profile, isolate local data snapshots and outboxes by active business, partition all Supabase rows and Realtime application with `business_id`, and use separate `CredEasy_Backup_<business-id>.json` Drive files for non-default businesses. The additive Supabase setup backfills existing data into the `default` business and must be applied before enabling multi-business cloud sync.
Profile information rows open editable bottom sheets, while Business Type and Category use selection screens; edits autosave through the durable profile outbox. QR and profile images are stored in app document files locally and referenced from the account-scoped business profile through the private Supabase media bucket. Business-card sharing previews the saved details and renders a PNG for the native share sheet.
The Help & Support “How to use CredEasy?” route opens the in-app topic guide; questions navigate to numbered step-by-step answers, and these screens hide the bottom tab bar. Help back buttons move Answer → Guide → Help → Ledger; Today’s transactions, Reports, Settings, Profile, and local legal pages return to their expected parent routes, and utility screens hide the bottom bar. The Ledger avatar opens the business chooser; selecting the active business opens its Profile, while selecting a different business switches its ledger and returns to Ledger. Each chooser row shows that business’s saved profile photo when available; Add another business creates an isolated workspace. The chooser does not expose business deletion. Inventory’s add-item action floats above the bottom bar.
The Help page links to in-app About CredEasy, Privacy & Security, and Terms & Conditions documents; Contact Us opens `mailto:help.credeasy@gmail.com`. The onboarding consent links open the same in-app legal documents. Preserve Android keyboard avoidance in the Profile field editor, including GSTIN and multiline address fields.
Ledger party search opens from a top-bar search toggle, and closing it clears the query. When no parties exist, show `assets/images/ledger-empty-state.png` in a compact contained frame, followed by “Add your first customer or supplier” and one Add Customer action; hide the dock add-customer button until a party exists, and keep search-with-no-matches as a separate state. Reports keeps PDF, CSV, P&L, cash-flow, and aging features, omits duplicate Google Drive backup entry points, and provides a back-to-Ledger control. Daybook is a date-range account statement with a PDF export for the currently selected period. The Ledger business profile avatar is circular; party-detail headers show each party's saved photo in a circular avatar (initial fallback when no photo exists). Today’s sales and collection tiles open date-and-type filtered transaction lists with a direct Ledger back button.
`formatMoney()` includes the rupee symbol; do not prepend another `₹` at call sites. Keep frequent tab switches immediate to avoid stutter.

Google sign-in and Google Drive file permission are mandatory before entering the app. Use one Supabase Google OAuth request with `openid email profile https://www.googleapis.com/auth/drive.file`; only verify the saved Drive grant after `signInWithGoogle()` has completed saving its provider token, since the auth-state update can arrive earlier. The Drive credential must belong to the same Google email as the app session. Do not add a skip path or a separate Drive sign-out control.
Google authentication must not mark onboarding complete. The standalone login route sends first-time users to onboarding and returning users to the tabs; only the onboarding finish action marks setup done. When the account-scoped local completion flag is absent, check the authenticated user's cloud `business_profiles` before treating them as new; a failed check must remain retryable rather than silently routing to onboarding.
Users may explicitly choose local-only offline mode without Google sign-in; offline mode keeps ledger data in AsyncStorage and disables cloud sync and Drive backup. For signed-in users, the first device to claim automatic Drive-backup ownership in Supabase uploads at most once per local day when opened; other devices only display the shared Drive backup status and upload when the user taps Back up now. Device ownership requires the additive `claim_drive_backup_device` setup in `docs/enable-transaction-realtime.sql`.
The onboarding access-choice step offers only two actions: Continue with Google and Continue offline. Both choices advance directly to business setup; successful Google authorization also auto-advances.
Authenticated devices using the same Google/Supabase account sync parties, transactions, bills, recurring entries, inventory and business-profile edits through durable local outboxes and Supabase Realtime. Every signed-in account and business has an isolated local snapshot; the explicit offline-only ledger uses its own scope, so changing Google accounts or businesses never uploads another scope's data. Legacy local data without a trustworthy owner remains in the offline scope. Queue entries are removed only after Supabase confirms each write; background failures remain queued for retry and are shown in Settings. Native AsyncStorage failures must propagate rather than succeed via an in-memory fallback. “Back up and remove” clears the complete active ledger and its queues only after every upload succeeds. Bill and recurring deletions use per-user, per-business tombstones; the additive SQL triggers reject later writes for deleted IDs. Scheduled follow-up reminders still have no active UI call site and remain device-local. Party, transaction and inventory deletion protections remain required; party deletion removes its transactions and requires Security PIN verification plus explicit confirmation. Existing parties' opening balances are shown as dated entries at the bottom of the party transaction history; edit/remove actions require the Security PIN, and the opening balance can also be edited or cleared to zero from the party edit screen. App resume retries sync. Offline mode never opens the Realtime channel. Enable the existing database with `docs/enable-transaction-realtime.sql` (safe, non-destructive; enables sync tables, RLS, guards, business partitions and Realtime publication) before expecting live cross-device updates.
Business workspace deletion requires Security PIN verification and explicit confirmation, refuses to remove the final workspace, and deletes cloud rows/media through the authenticated `delete_business_workspace` RPC before local snapshots are removed. The additive SQL setup records deletion tombstones and blocks stale devices from recreating deleted profiles; rerun it before using workspace deletion.
Party, transaction and profile images are copied into app document storage, backed up with Android app data, and synced through the private `credeasy-ledger-media` Supabase bucket; references are account-path checked and downloaded to local files on cloud pulls. The additive Supabase setup also creates the private bucket/policies and restrictive account-update guards. Account deletion removes that user's objects from the private media bucket before deleting the Supabase Auth user; the client verifies the current session, preserves local data on remote failure, and displays the backend/upstream status. Deploy backend changes and configure `SUPABASE_SERVICE_ROLE_KEY` on the backend host before expecting remote account deletion. Android OS-managed backup can restore offline-only AsyncStorage and image files after reinstall, but only when device backup/transfer is enabled and successful; it is not guaranteed and excludes SecureStore credentials.
Native Google OAuth uses Supabase PKCE: pass the `credeasy://` `redirectTo` to `signInWithOAuth`, then exchange the returned callback `code` with `exchangeCodeForSession()` before requiring the provider's Drive token. Keep support for existing implicit-flow token callbacks. The required-access route gate must recheck Drive permission on route transitions, must not redirect based on stale access state while a check is pending, and must keep the root Stack mounted while showing any pending-access overlay; unmounting it during route changes can trigger React Navigation update-depth crashes. The login screen owns its `/tabs` redirect in one guarded effect; do not also navigate to tabs from the OAuth button handler.
Normalize bare `credeasy://` root intents to `/` in `app/+native-intent.tsx`, preserving OAuth query/hash callbacks; keep `app/+not-found.tsx` as a recoverable Ledger route for invalid external paths. Migrate legacy profile image URIs out of ImagePicker cache only when files still exist; missing cache files should be cleared and the user prompted to reselect, never block Profile or business-card sharing.

## Tech Stack
- **Frontend:** React Native / Expo (TypeScript, Strict TypeScript)
- **Backend:** Python/Flask (`backend/`)
- **Database:** Supabase (Postgres, Auth, RLS, Storage)
- **Auth:** Supabase OAuth (Google)
- **Ads:** AdMob via `react-native-google-mobile-ads`
- **Storage:** AsyncStorage (primary), Google Drive (backup/recovery), Supabase (auth and legacy sync)

## Key Constraints (Do Not Break)

### Cloud Sync Architecture
- **Supabase cloud sync is unreliable** - do not "fix" sign-out data clearing until sync is verified
- **Google Drive is the reinstall recovery path** - backup/restore is tied to the signed-in Google account and Drive permission
- Supabase expects UUIDs; legacy local IDs may still fail to sync
- AsyncStorage remains primary; Google Drive is used for backup/recovery after Drive access is granted
- See `docs/FIXING-GUIDE.md` for the repair order if/when sync is prioritized

### Auth/Session Issues
- Client stores Supabase JWT; backend uses `st_...` tokens in `db.user_sessions` — different systems
- `saveToken()` in auth lib is defined but never called
- `/api/auth/session` endpoint is dead code
- Google OAuth currently requests Drive file access for automatic backup; review this scope if auth changes
- Client rebuilt per call with `persistSession: false` — no persistent Supabase session

### Database Schema
- New records use UUIDs; legacy local records may still have string IDs
- Supabase expects UUID primary keys, so legacy IDs may fail cloud upserts
- Google Drive backups, not Supabase sync, are used for reinstall recovery
- `docs/supabase-migration.sql` declares UUID primary keys (migration needed)

### RLS Policies
- UPDATE policies have `USING` but no `WITH CHECK` (users can reassign row `user_id`)
- `business_profiles` has no DELETE policy
- RLS IS enabled with `auth.uid() = user_id` policies (correct)
- `EXPO_PUBLIC_SUPABASE_ANON_KEY` is designed to be public — RLS is the access control
- `service_role` key must never ship

### Other Known Issues
- AdMob is enabled for the free, ad-supported app
- Backend 401s on all authenticated calls (voice assistant included)

### Android Build Fix (Resolved 2026-09-04, updated 2026-09-04 v2)
Local `./gradlew assembleDebug` / `assembleRelease` now works on Windows + NDK 27. The fix lives in two places:
1. **`patchCxxSharedLib` Gradle task** (`android/app/build.gradle`, runs before every native build via `preBuild.dependsOn patchCxxSharedLib`): walks every `CMakeLists.txt` under `react-native-screens`, `react-native-worklets`, `react-native-reanimated`, `react-native-gesture-handler`, `react-native-safe-area-context`, `react-native-webview`, `react-native-google-mobile-ads`, `react-native-audio-api`, `expo-modules-core`, and `@react-native-async-storage/async-storage`. For each file: (a) inserts `find_library(CPP_SHARED_LIB c++_shared)` before the first `add_library(...)` if missing; (b) walks every `target_link_libraries(...)` call (handles both single-line `target_link_libraries(foo bar)` and multi-line `target_link_libraries(\n  foo\n)` forms via balanced-paren matching) and appends `${CPP_SHARED_LIB}` to any block that doesn't already have it. The patch is idempotent — re-running on an already-patched file is a no-op. Survives `gradle clean`, `npx expo prebuild`, and `yarn install`.
2. **Standalone Node.js patcher** (`frontend/scripts/patch-all-cmake.js`): same logic in plain JS for one-off pre-patching without running gradle. Useful if you need to inspect or fix files before a long build, or to understand which blocks were patched.
**Known cosmetic warning:** `CMAKE_OBJECT_PATH_MAX=250` warning on Windows for paths with spaces — non-fatal, build proceeds. APKs at `frontend/android/app/build/outputs/apk/debug/` and `.../release/`.

## File Locations

### Frontend
```
frontend/src/
├── lib/
│   ├── auth.tsx          # Supabase auth, signIn/signOut
│   ├── google-drive.ts   # Google Drive backup and restore
│   └── supabase.ts       # CloudSync, pushToCloud
├── components/ads/
│   └── BasicBanner.native.tsx  # AdMob banner
└── utils/storage/
    └── storage-service.ts      # AsyncStorage wrapper
```

### Backend
```
backend/
├── server.py             # Flask app, /api routes
├── requirements.txt
└── .env                  # SUPABASE_URL, SUPABASE_ANON_KEY
```

### Documentation
```
docs/
├── FIXING-GUIDE.md       # OAuth round-trip repair order
├── supabase-migration.sql # UUID migration script
└── FIXES_APPLIED.md      # Fix history log
```

---

# My Instructions

## User Preferences

### About
- **Name:** Monodeep Deb
- **Platform:** Windows 11, Git Bash / PowerShell

### Coding Style
- Keep code minimal and clean
- Comments explain "why," not "what"
- Prefer established libraries over custom implementations
- Type hints in Python, strict TypeScript

### Preferences
- **Language:** TypeScript (frontend), Python 3 (backend)
- **Framework:** React Native / Expo (frontend), Flask (backend)
- **Package manager:** npm (Node), uv or pip (Python)
- **Testing:** TBD
- **Linting:** TBD

### Git Workflow
- Branch naming: `type/short-description` (e.g., `feat/auth-flow`, `fix/api-timeout`)
- Prefer small, focused commits over large ones
- Don't commit unless asked

### Communication
- Be concise — no filler, no preambles
- When presenting options, give a recommendation with reasoning
- When stuck or uncertain, say so immediately rather than guessing
- **If a request is ambiguous or unclear, stop and ask targeted questions before acting**
- Use plan mode for non-trivial tasks
- Never include time estimates, durations, or period-based roadmaps

### Error Handling
- Surface errors early, fail fast
- Log with structured context, not bare messages
- Don't add defensive error handling for impossible cases

### MCP Config
- MCP servers go in `.mcp.json` (project root) or `~/.claude.json` — never in `settings.local.json` (permissions only)

### My Vault
Personal knowledge base at `~/.claude/my_vault`. Start with `index.md` — it tells you what's here and when to read each file. This is persistent context (decisions, project state, terminology), not rules.

---

## Navigation Protocol

BEFORE starting any task:

1. Read `.claude/docs/index.md` — infer where to find relevant information
2. Read ONLY the matched file(s)
3. **Never** retrieve all `.md` files in one call
4. For multi-domain tasks, check the Combos table for pre-mapped file sets
5. If nothing resonates, work from the codebase directly
6. If information exists in a doc but isn't reflected in `index.md`, add it there concisely

---

## Browser QA Protocol

**Applies when:** browser-testing or UI verification via Playwright.

- Act as a senior full-stack engineer. Navigate methodically, read console errors, inspect snapshots.
- **Never skip, suppress, or retry-loop past errors.** Every error is a signal — trace it to source.
- **Small/medium fixes** (wrong routes, missing props, styling, null checks): fix immediately, re-test.
- **Major fixes** (architecture, migrations, >3 files): present findings and proposed fix first.

---

## HANDOFF Protocol

At the end of each feature implementation:

1. **Summarize the completed feature in 1-2 sentences** in HANDOFF.md
2. **Write a CLAUDE.md file** at the project root (exactly like this) capturing project-specific context, decisions, and current state

---

## Startup Memory

```
name: credeasy-deferred-auth-sync-workstream
description: "CredEasy's cloud sync and auth are architecturally broken and were deliberately left unfixed in the Aug 2026 audit — do not 'fix' sign-out data clearing."
originSessionId: 2dd5b8cc-a133-40dc-aeec-632af0085949
modified: 2026-08-26T08:42:19.952Z
```

See `memory/credeasy-deferred-auth-sync-workstream.md` for full details on auth/sync issues and repair order.

## Marketing Website

`website/index.html` is a standalone responsive product site for `https://credeasy.live`. Keep copy limited to verified CredEasy capabilities; do not add unverified store URLs, pricing tiers, performance claims, language counts, integrations, or testimonials. The green-led, product-first homepage uses the app mark at `website/assets/credeasy-mark.png`, privacy-redacted Ledger, Inventory, and Billing screenshots in `website/assets/`, and shared styles in `website/site.css`. Preserve its responsive navigation, accessible product tabs, dark/light theme toggle, FAQ disclosures, scroll reveals, restrained hero motion, and reduced-motion support. The cPanel static upload is `credeasy-live-godaddy.zip`; the separate GoDaddy Managed WordPress upload is `credeasy-wordpress-theme.zip`, built by `website/build-wordpress-theme.py`. The theme uses `front-page.php` plus legal templates for WordPress pages with slugs `privacy-policy` and `terms-and-conditions`. See `docs/WEBSITE-GODADDY-DEPLOYMENT.md` for both routes. Offline-only use stays local; describe Drive backup only for users who sign in and grant Drive access.

The app logo uses the supplied dimensional green C-and-upward-arrow mark. Keep `frontend/assets/images/logo.png`, `icon.png`, `adaptive-icon.png`, `splash-image.png`, the Android mipmap variants, and `website/assets/credeasy-mark.png` visually aligned with the latest supplied image.

## Launch Readiness Audit

Onboarding must not mark setup complete unless saving the business profile succeeds. Backend body limits must be enforced on streamed/chunked requests as well as `Content-Length`, while file endpoints allow multipart framing but retain exact per-file limits. OpenTelemetry remains disabled unless a collector/Phoenix endpoint is explicitly configured. `frontend/.env` is local-only, gitignored, and excluded from the frontend repository; retain a local copy, but rotate any private value that was committed in the past. EAS `preview` produces an APK and `production` produces an AAB; configure required app variables and signing credentials in EAS. Local Gradle release APKs use the debug keystore for QA only. Native ad placements stay on Google test IDs per project requirement and are not monetized inventory.

The frontend locks patched versions of `brace-expansion`, `image-size`, `js-yaml`, `postcss`, `tar`, and `undici`; keep `package.json`, `yarn.lock`, and `package-lock.json` aligned. `npm audit --omit=dev --audit-level=high` should pass. Four moderate npm advisories remain in the Expo Router/query-string URL-decoding chain; do not force a router major change without compatibility testing.

## Account-Aware Onboarding

Google onboarding completion is stored per Supabase user ID; local-only offline setup remains device-scoped. When upgrading from the older device-wide completion flag, bind it to the currently signed-in account before sign-out so a newly selected Google account must complete business setup.

The Ledger avatar opens the business chooser. Selecting the active business opens its Profile; selecting another business switches to that Ledger. Business rows show the saved business profile picture when available. Compact tagged CredEasy CSV imports must retain all parties and transactions without importing “You’ll Give”/“You’ll Get” summary labels or closing-balance artifacts. Inventory refreshes reconcile stable `low-stock:<itemId>` notifications into the persisted notification list and preserve read state across refreshes.

Inventory's Export all action shares a CSV containing every locally stored item and movement-history record, independent of the active view or search filter; keep the stock/tax metadata and movement sections in `src/utils/inventory-csv.ts`. The add-customer contact chooser filters on-device by name or phone. Resolve cloud business profile photos and QR images to durable local files before rendering or sharing them; WhatsApp reminders must attach the QR or clearly report a failed attachment. When a queued inventory movement references an item already removed locally, persist its deletion tombstone before uploading the historical movement so it remains in history without blocking sync. Account deletion depends on the latest backend deployment with `SUPABASE_SERVICE_ROLE_KEY` configured.
OkCredit backup-summary CSVs may have fused `NAMEMOBILEADVANCEDUE`/`NAMEMOBILEDUEADVANCE` headers and packed party rows; import the customer/supplier advances and dues as signed opening balances, and state that the backup has no transaction history. PDFs convert to CSV through the local parser backend before on-device CSV parsing and review; DOCX is not a supported import type. WhatsApp reminders are available only for customer parties with a positive receivable balance, which the handler rechecks before sending. For Android WhatsApp QR reminders, stage the image under app cache because react-native-share's FileProvider only exposes cache and Downloads paths; include the normalized recipient with the targeted image share and use internal cache storage. Patched native handlers must preserve the `ACTION_SEND` image payload, set the WhatsApp package and recipient JID, then dispatch exactly once; do not force the private Conversation activity, which opens the chat without the QR attachment. Opening a notification marks it read, removes it from the visible list, and persists its dismissed ID so generated ledger notifications do not immediately return. App Lock can be configured after onboarding from Preferences; creating a PIN enables it, and PIN changes require the existing PIN. Party edit, PDF export and deletion stay in the party-detail overflow menu, with existing Security PIN protections preserved. The onboarding app PIN is optional, transaction-entry keyboards must accept decimal values, and every native ad placement must use Google's test unit IDs/app IDs on all devices; initialize the shared SDK once before requests and render native ad assets inside `NativeAdView`. The supplied green-square C-and-arrow logo is the source for app, launcher, splash, favicon, and website marks; Android adaptive icon background must match its green. The `AppTheme` must define `splashScreenIconSize` for AndroidX's compat splash layout on pre-Android-12 devices.

Recent release follow-up: Text-only WhatsApp reminders use a direct chat deep link; QR reminder shares must resolve as targeted shares or report/timeout rather than remain indefinitely “Opening…”. Onboarding now imports CSV files only and reviews them on-device; do not restore PDF or Excel import choices without an explicit product request. Deploy backend account-deletion changes with `SUPABASE_SERVICE_ROLE_KEY`; never include that key in the app.

Latest UI follow-up: The Ledger omits the standalone You Gave/You Got shortcuts, Recent transactions block, and Today's sales/collection tiles; keep Quick links aligned with their cards. Daybook is a date-range account statement. Chotu is the voice helper; stock and ledger writes require a separate confirmation. QR reminders try targeted WhatsApp Business/WhatsApp shares first, then offer the native share sheet with the QR attached if direct targets fail. The login screen supports both Google and explicit offline continuation; keep both routes and their existing onboarding behavior intact when refining its visual design. Standalone Android installs must use the release APK, which embeds the JavaScript bundle; debug APKs require Metro. Keep branded progress visible for asynchronous startup checks and do not block the root app shell on optional icon-font loading.

Native Chotu microphone startup requests permission once through Expo Audio, then only checks permission state through `react-native-audio-api`; do not trigger a second native permission request. Haptic failures on the microphone control must be caught so they cannot interrupt recording startup.
The Settings "Back up and remove" action displays a blocking branded wait screen while the existing cloud-push-before-local-clear sign-out runs; failures remain visible and never clear local data unless the cloud push succeeds. Party phone numbers are optional when adding or editing a party, but any supplied number must remain a valid 10-digit Indian mobile number. Ledger amount entry preserves fractional rupee amounts, including values below ₹1; Hindi and ASCII digit parsing must not truncate decimals or grouped thousands.
Required Google Drive authorization is still rechecked on route transitions, but do not block navigation with the full-screen loading panel when revalidating the same account and offline-mode context. Keep the gate visible on initial verification and when the account or offline scope changes, and only redirect after the fresh check completes.

Chotu speech normalizes rupee amounts to words in the shared TTS request helper so both in-app and widget replies pronounce grouped values such as ₹1,265 correctly; keep backend TTS formatting/regression coverage aligned. Settings account deletion must remain explicitly destructive, require Security PIN verification, call the existing `deleteAccount()` auth method, and surface service failures without clearing local data on remote failure.

The installed Android build's API URL is `https://credeasy-api-634736672458.asia-south1.run.app` (Cloud Run, `asia-south1`); the Settings account-deletion error about missing `SUPABASE_SERVICE_ROLE_KEY` must be fixed on that Cloud Run service using a Secret Manager reference, never in the app or its `.env`. See `docs/CLOUD-RUN-ACCOUNT-DELETION.md`. The Render API/static hosts serve separate clients; verify the exact client's configured backend before changing hosting settings.

Backend Cloud Run deployments use the root `cloudbuild.yaml` and `backend/Dockerfile`; the backend Docker context excludes `.env` and `.env.*`. The Cloud Build trigger watches a pushed repository branch, pushes the backend image to the `credeasy-api-images` Artifact Registry repository in `asia-south1`, and updates the existing `credeasy-api` image. Cloud Build needs Artifact Registry Writer, Cloud Run Admin, and Service Account User on the service runtime account. The runtime account separately needs Secret Manager Secret Accessor for backend secrets. Never place provider or Supabase secret values in the Dockerfile, Cloud Build configuration, or app; verify the deployed revision and its Secret Manager bindings after each release. The Render API/static hosts serve separate clients; verify the exact client's configured backend before changing hosting settings.
