# CredEasy - Feature Handoff Log

## Template
**Feature:** [Feature name]
**Status:** [Completed/In Progress/Blocked]
**Summary:** [1-2 sentences on what was done]

---

## Feature History

<!-- Add completed features below this line -->

### 2026-09-04 — UPI deep link in WhatsApp reminders
**Feature:** One-tap UPI payment from WhatsApp reminder messages
**Status:** Completed
**Summary:** All three WhatsApp reminder builders now append a `upi://pay?pa=...&pn=...&cu=INR` deep link when the business has a UPI ID configured. WhatsApp renders the link as a tappable line that opens the user's UPI app directly with the merchant pre-filled. Files: `app/party-detail.tsx:106-125` (single-party reminder), `app/(tabs)/index.tsx:155-159` (single-party from dashboard), `app/voice-assistant.tsx:523-535` (voice command). Each builder was changed from a plain text VPA (`merchant@okaxis`) to a structured message with the UPI deep link on its own line. The QR code image already configured in Settings is not sent directly — `whatsapp://send?text=` doesn't support attachments; the deep link is the universally-compatible fallback. TypeScript clean.

### 2026-09-04 — Google Drive backup (replaces broken Supabase cloud sync)
**Feature:** Per-user Google Drive backup — user owns the file, restore on any device
**Status:** Completed (needs Google Cloud Console client ID to test)
**Summary:**
Replaced the never-working Supabase cloud sync with a user-owned Google Drive backup. The app now:
1. Opens Google OAuth2 (PKCE) flow via `expo-auth-session` (Expo SDK 54-compatible v7.0.11), scopes to `drive.file` (only files this app creates).
2. After the user signs in, exchanges the auth code for an access token (with `access_type=offline` so refresh tokens come back).
3. Stores the access token in AsyncStorage and uses it to call the Google Drive REST API directly — finds or creates a "CredEasy" folder, then finds or uploads `CredEasy_Backup.json` using `multipart/related`. Restore downloads `?alt=media` and pipes through existing `StorageService.importAllData()` (which already validates schemaVersion 1).
4. New screen `app/google-drive-backup.tsx` replaces the old Supabase sync card in `app/(tabs)/reports.tsx`. Card UI: signed-out shows "Sign in with Google" button, signed-in shows email, file size, last-modified timestamp, and "Back up now" + "Restore from Drive" buttons (restore prompts a confirmation alert).
5. `useFocusEffect` refreshes the file info every time the screen opens, so after a backup the UI immediately reflects the new file size/timestamp.
6. `expo-auth-session@7.0.11` added to `package.json`. `EXPO_PUBLIC_GOOGLE_CLIENT_ID` added to `.env.example`.

**Setup required by user:** Create an OAuth 2.0 Web Client ID at https://console.cloud.google.com (project → APIs & Services → Credentials → Create OAuth client ID → Application type: Web application → Authorized redirect URIs: `http://localhost`). Set `EXPO_PUBLIC_GOOGLE_CLIENT_ID` in `frontend/.env` to the Web Client ID. The app uses `makeRedirectUri({preferLocalhost: true})` which resolves to `http://localhost` on web/native. **Why this is the right fix:** Supabase sync requires fixing the UUID/string-ID schema mismatch first (see `docs/FIXING-GUIDE.md`); Google Drive uses the user's own account, so the data lives outside our backend — no schema migration needed. The plan file `C:\Users\Monodeep\.claude\plans\structured-honking-unicorn.md` documents the original approach; the v7 API differences (`AuthRequest` class with `promptAsync` instead of v8's `startAsync`, `exchangeCodeAsync` from TokenRequest) required adapting the implementation.

**Why I removed the Supabase UI from `reports.tsx` but left the lib file:** `src/lib/supabase.ts` is still imported by `src/lib/auth.tsx` and the login screen — don't touch it. Only the Supabase sync card in `reports.tsx` was removed. The `getLastBackupTime()` reading the local `LAST_BACKUP_KEY` is a thin replacement for the old `CloudSync.getLastSyncTime()` call.

### 2026-09-04 — Dashboard & Onboarding UX + PartyDetail crash fix
**Feature:** Consolidated UI improvements: onboarding step reorder, home dashboard cleanup, PartyDetail crash fix
**Status:** Completed
**Summary:**
- **PartyDetailScreen crash fix:** Moved all `useMemo`-based calculations (`accruedInterest`, `creditDaysOverdue`, `displayedTxs`) before the early returns (`if (loading)` / `if (!party)`). The original code called `sortedTxs` (which referenced `txTime` defined later) and several `React.useMemo` hooks after the early returns — React threw "Rendered more hooks than during the previous render" because hooks ran in different counts on first vs second render. All derived state now sits before the early-return guards. Also removed orphaned `txTime` reference by moving the helper to the top of the component function body (still hoisted by JS function declaration semantics).
- **Onboarding step reorder:** Google OAuth sign-in moved from step 4 → step 2 of the 6-step flow. New order: Welcome → Business Setup → Google Sign-in → Terms → Import → PIN. Step navigation (`goToStep`) and the progress indicator are unchanged — they reference `step` dynamically.
- **Home dashboard cleanup (index.tsx):** Removed the "Cash Flow — This Week" mini chart (was #N4 placeholder) and the top overdue widget (#7). Replaced the search-icon button in the top bar with a notification icon (`Ionicons name="notifications-outline"`) that shows a red badge with the count of overdue parties and navigates to `/(tabs)/reports` (which now hosts the full cash flow chart). Cleaned up unused imports (`toMoney`) and unused `useMemo` computations (`cashFlow`, `maxCashFlow`, `topOverdue`).
- **Reports screen enhanced (reports.tsx):** Added a full N4 Cash Flow chart card to the reports tab (the one removed from home), reusing the same `cashFlowByDay` ledger helper and matching the dashboard's visual style (green/red bars, legend). Added `cashFlowByDay` import and the matching styles. Supabase sync remains in place per project constraints — not yet replaced with Google Drive.

### 2026-09-04 — EAS preview APK shipped (js-yaml + .easignore fix)
**Feature:** Get a working APK via EAS cloud build
**Status:** Completed
**Summary:** First EAS build (5adecca2) errored in Install dependencies — `package.json` resolutions forced `"**/js-yaml": "3.1.7"`, which was never published (latest 3.x is 3.15.1); yarn on EAS rejected it. Fixed both `**/js-yaml` and `**/@istanbuljs/load-nyc-config/js-yaml` to `3.13.1`. Second attempt failed upload — local Gradle daemons held `android/.gradle/` lock files (EBUSY). Added `.easignore` excluding `android/.gradle/`, `android/build/`, `android/app/build/`, `node_modules/.cache/`, `*.apk`, `*.aab`. Third build (1912f6a5) succeeded: preview/internal, SDK 54, v2.17.3. APK: https://expo.dev/artifacts/eas/O2eSKxc09HIzaMfDxHJ9sr9ii9rGS9bt1Z-3CjA2jRc.apk

### 2026-09-04 — Android local build unblocked (c++_shared + splashscreen fix)
**Feature:** Fix local Windows NDK 27 Android build: c++_shared linking + dangling splashscreen theme
**Status:** Completed
**Summary:** Two unrelated failures blocked `./gradlew assembleDebug` on Windows + NDK 27: (1) New-Arch C++ modules (`react-native-screens`, `react-native-worklets`, `react-native-reanimated`, `expo-modules-core`, plus 8 auto-generated codegen CMakeLists under `*/build/generated/source/codegen/jni/`) referenced `operator new`, `std::bad_alloc`, `__cxa_throw`, `std::__ndk1::*` symbols at link time but the linker wasn't being told to link `libc++_shared.so` — even though `-DANDROID_STL=c++_shared` was set. (2) `Theme.App.SplashScreen` was still in `android/app/src/main/res/values/styles.xml` and referenced by `AndroidManifest.xml` but the `drawable/splashscreen_logo` it pointed to had been removed in the 2026-09-01 splash removal — resource linking failed. Fix: (1) added `find_library(CPP_SHARED_LIB c++_shared)` + `target_link_libraries(... ${CPP_SHARED_LIB})` to all source-level CMakeLists (hand-edited), and added a Gradle `patchCxxSharedLib` task in `android/app/build.gradle` (wired via `preBuild.dependsOn`) that idempotently patches the auto-regenerated codegen CMakeLists on every clean build — survives `npx expo prebuild` and `gradle clean`. (2) removed `Theme.App.SplashScreen` from `styles.xml` and changed `AndroidManifest.xml:27` activity theme to `@style/AppTheme`. `./gradlew assembleDebug` succeeds (189MB APK, all 4 archs). `./gradlew assembleRelease` succeeds (99MB APK, all 4 archs, all 22 native libs per arch including `libc++_shared.so`). Both APKs at `android/app/build/outputs/apk/{debug,release}/`. No more reliance on EAS cloud build or the stale 49.8MB fallback. **Why the prior 2026-09-03 attempt failed:** that session patched `target_link_libraries(... c++_shared)` directly (CMake treats `c++_shared` as an unknown target name in modern NDK toolchains) instead of using `find_library` first; the present fix follows the [official NDK samples](https://github.com/android/ndk-samples/blob/main/hello-cmake/app/src/main/cpp/CMakeLists.txt) pattern. **Known cosmetic warning** (non-fatal): CMake's `CMAKE_OBJECT_PATH_MAX=250` warning on Windows for paths containing the long username + spaces — the build proceeds correctly past it.

### 2026-09-04 — Security audit fixes round 2 (env vars + CORS)
**Feature:** Security audit follow-up — restore missing backend Supabase env vars, restrict CORS methods, fix SMS parser base URL
**Status:** Completed
**Summary:** `backend/.env` was missing `SUPABASE_URL` and `SUPABASE_ANON_KEY` (only had `SUPABASE_SERVICE_ROLE_KEY`); all authenticated backend calls were 500ing because `get_authenticated_user()` short-circuited on the empty values. Added both keys (matching the Supabase project in `frontend/.env`). `backend/server.py:1240` CORS methods restricted from `["*"]` to `["GET", "POST", "DELETE", "OPTIONS"]` (the only methods actually used). `frontend/app/sms-parser.tsx:43` was reading `EXPO_PUBLIC_API_BASE_URL` (unset) instead of `EXPO_PUBLIC_BACKEND_URL` — fixed so SMS parsing no longer posts to `null`. `backend/.env` and `.env.example` cleaned of obsolete `MONGO_URL` / `DB_NAME` keys from the previous Mongo era. `npx tsc --noEmit` clean; `npx expo export --platform android` succeeds. **Remaining:** 9 high-severity npm advisories in `metro`, `@expo/*`, `image-size`, `postcss` — all require Expo SDK 57 (breaking) to fix non-vulnerably; flagged for user decision. Cloud sync remains intentionally broken per project constraints.

### 2026-09-04 — OpenTelemetry + Phoenix tracing on backend
**Feature:** Auto-instrumented LLM/Whisper/TTS calls with OpenTelemetry, exporting to Arize Phoenix
**Status:** Completed (no APK rebuild needed — backend-only)
**Summary:** Foglamp (Vercel AI SDK observability) is not applicable — this app's AI runs in `backend/server.py` using Python `openai` + `groq` SDKs, not the `ai` npm package. Replaced with OpenTelemetry + Phoenix. Added `_setup_telemetry(app)` to `server.py` that wires a `TracerProvider` with `OTLPSpanExporter` → `http://localhost:6006/v1/traces` (Phoenix default), `FastAPIInstrumentor.instrument_app(app)`, and `OpenAIInstrumentor().instrument()` (covers both `AsyncOpenAI` and `groq.AsyncGroq` since Groq uses the OpenAI SDK format). Tracer provider, service name, and version follow OTel semantic conventions. Prompt/completion content capture is opt-in via `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_and_event` (default on; flip to `no_content` for privacy). Set `OTEL_SDK_DISABLED=true` to disable without code changes. `requirements.txt` gained 5 packages. Smoke-tested: `server.py` imports cleanly with telemetry disabled; all OTel packages import cleanly when enabled.

### 2026-09-04 — Phase 5 + Phase 6 Feature Implementation
**Feature:** All remaining features from docs/FEATURES.md (Phase 5: Data Management + Phase 6: Mobile-specific)
**Status:** Completed
**Summary:**
Phase 5 — Data Management:
- **#13 Categories:** Predefined category chips (Groceries, Rent, Utilities, Transport, Medicine, Food, Other) added to add-transaction.tsx. Passed to both addTransaction and updateTransaction. Optional `category?: string` field on Transaction interface.
- **#14 Transaction Editing:** Edit pencil button added to each transaction row in party-detail.tsx. Navigates to `/add-transaction` with `editTxId` param. `global.addTxParams` bridge used since expo-router params are async. `updateTransaction()` method added to storage-service. Updates the existing transaction instead of creating a new one.
- **#17 Recurring Transactions:** Full CRUD (`getRecurring`, `saveRecurring`, `addRecurring`, `deleteRecurring`, `updateRecurring`) in storage-service. New screen `app/recurring-transactions.tsx` with list, due-items warning card, and add-form modal. Frequency: daily/weekly/monthly. Link added in Settings under "Recurring Transactions" card. `advanceNextDue()` and `getDueRecurring()` ledger helpers handle due-date logic.
- **N8 Multi-Language:** `lang` state upgraded from `'en' | 'hi'` to `string`. Language picker modal in settings.tsx with 9 languages (English, Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, Kannada, Punjabi). Full translations for en/hi; others fall back to English strings. `t` accessor casts to `(translations as any)[lang] ?? translations.en`.
- **#16 Customer Photo:** Camera/gallery photo capture via expo-image-picker added to add-party.tsx (circular preview, change/remove). `photoUri` stored on Party. Dashboard (index.tsx) shows photo in party avatar if set. Party-detail header shows photo next to name.

Phase 6 — Mobile-specific:
- **#15 Local Notifications:** `expo-notifications` added to package.json. `src/utils/notifications.ts` provides `requestNotificationPermission`, `scheduleFollowUp` (fires tomorrow 9am by default), `cancelNotification`, `listScheduledNotifications`. Bell icon button added to party-detail action bar triggers the scheduler.
- **#18 Inventory:** `Item` interface in mock.ts (id, name, currentStock, lowStockThreshold, unit, price). Full CRUD in storage-service (`getInventory`, `saveInventory`, `addItem`, `updateItem`, `deleteItem`) using `@credeasy_inventory_v1` key. New screen `app/inventory.tsx` with search, low-stock alert banner, FAB to add, inline edit on tap, delete with confirmation. Settings link under "Inventory" card.
- **#21 SMS Auto-Parsing:** `POST /api/sms/parse` endpoint in backend (before `/api/import/parse`). Regex pass tries HDFC/SBI/ICICI/Kotak UPI SMS patterns (Rs. X debited/credited, UPI Ref, date). Falls back to Groq LLM (`llama-3.1-8b-instant`) if confidence < 0.6. Returns `{ amount, party_name, party_phone, type, reference_id, date, confidence, parser }`. Frontend `app/sms-parser.tsx` with paste area, sample SMS, parse button, confidence badge, and "Add as Transaction" button that pre-fills `/add-transaction`. Settings link under "Bank SMS Parser" card.

### 2026-09-03 — TTS fix + PDF/DOCX import in onboarding (build blocked on Windows)
**Feature:** Voice assistant TTS streaming + optional PDF/DOCX ledger import during onboarding
**Status:** Code complete; local Android build blocked by Windows + NDK 27 + react-native-worklets toolchain incompatibility
**Summary:**
- **TTS fix (backend, `backend/server.py`):** Replaced the buffered Edge TTS approach with a real `async def audio_generator()` that yields `edge_tts.Communicate(...).stream()` chunks directly into a `StreamingResponse(media_type="audio/mpeg")`. The first client now gets audio as it's generated, so the player no longer times out waiting for a full file.
- **Import feature (backend, `backend/server.py`):** New `POST /api/import/parse` endpoint accepts `multipart/form-data` PDF or DOCX, extracts text via `pdfplumber` / `python-docx`, then regex-matches Indian phone numbers (10-digit, +91), rupee amounts (₹, Rs., INR, k/lakh suffixes), transaction directions (Gave/Got, Debit/Credit, Dr/Cr), and dates (DD/MM/YYYY, ISO). Returns `{ parties, transactions, warnings }` for the user to review before saving.
- **Import feature (frontend, `frontend/app/onboarding-import.tsx`):** New `ImportStep` component (file picker, parse, preview, save) inserted between `TermsStep` and `SignInStep`. `TOTAL_STEPS` updated 5 → 6. Strict "Skip for now" button. `expo-document-picker` 14.0.8 added to `package.json`. New `addTransactionWithDate()` method on `storage-service` preserves original transaction dates during import.
- **Health endpoint (backend, `backend/server.py`):** Added `GET /api/health` returning `{ status, service, time }` for monitoring.
- **Voice assistant (frontend, `app/voice-assistant.tsx`):** Removed `as any` type assertions; added content-type logging and clearer error reporting for TTS failures.
- **Local build BLOCKED on Windows:** Tried every NDK installed (25.1, 26.3, 27.0). NDK 27 with `c++_shared` patched into `react-native-worklets`, `react-native-reanimated`, `react-native-screens`, `expo-modules-core` `target_link_libraries` advances further (no `operator new` errors) but still fails with `undefined symbol: std::bad_array_new_length` from `libc++_shared.so`. NDK 26.3 fails at CMake configure (`c++_shared` is not a valid CMake target — the toolchain uses `-DANDROID_STL=c++_shared` as a flag, not a target name). Windows native builds of React Native 0.81 + react-native-worklets are not yet supported upstream. Use EAS cloud build (macOS worker) or build from WSL/Linux. The previous `credeasy-release.apk` (49.8 MB) is restored from git as a fallback for testing.
- **Reverted all CMake patches** in `node_modules/`. Repo is back to a clean state.

### 2026-09-01 — Security PIN, transaction delete, account delete, T&C consent, PDF fix
**Feature:** Security PIN system, transaction deletion, account deletion, Terms & Privacy Policy onboarding consent, PDF direct download on Android
**Status:** Completed
**Summary:** Added a separate Security PIN system (4-digit, stored in AsyncStorage) distinct from App Lock PIN. `SecurityPinModal` component handles verify/set/confirm flows. Transactions in party-detail now show a delete button (trash icon) with PIN verification before deletion. Added `DELETE /api/auth/account` endpoint in backend (uses `SUPABASE_SERVICE_ROLE_KEY`) and `deleteAccount()` in auth lib that calls backend, clears local data, and signs out. "Delete Account" button in Settings requires PIN. Added Terms & Privacy Policy step (step 3) in onboarding with mandatory checkboxes — both documents open in external browser via `Linking.openURL`. Fixed PDF generation on Android by using `Linking.openURL` to open the PDF directly in the system viewer instead of relying on the share sheet. Fixed expo-file-system v15+ API change (`documentDirectory` → `Paths.document.uri`) with type-cast fallback. Created `docs/TERMS-AND-CONDITIONS.md` (18 sections) and updated `docs/PRIVACY-POLICY.md` with real contact email. TypeScript and Python syntax checks pass. Frontend committed as `3777229`, parent updated to point to it.

### 2026-09-01 — MongoDB removed from backend, QR upload, contact modal, UPI removed
**Feature:** Backend MongoDB removed, onboarding step reorder, business QR code upload, full-contacts picker, UPI removed from party detail, SMS auto-send removed
**Status:** Completed (APK build pending)
**Summary:** Removed `motor`, `pymongo`, and `AsyncIOMotorClient` from `backend/server.py` — the voice assistant routes (`/api/voice/transcribe`, `/api/voice/speak`, `/api/voice/assist`) only need OpenAI + Supabase auth, no database. `requirements.txt` updated. Moved Google sign-in to step 2 of onboarding (before PIN step 3): order is now Welcome → Business → Sign-in → PIN. Added `qrCodeUri` to `BusinessProfile` and `expo-image-picker` for upload in both onboarding (SetupStep) and Settings (Business Profile card) with preview, change, and remove. Removed the auto-SMS send on every transaction in `add-transaction.tsx`. Removed the UPI "Pay" button from `app/party-detail.tsx`. Rewrote the contact picker in `add-party.tsx` to open a `Modal` with a `FlatList` of every contact that has a valid 10-digit Indian mobile. The voice assistant still fails with "network request failed" because the backend is at `http://10.174.0.44:8000` (private LAN IP); improved error messages to show a clear Hindi/English "Cannot reach the server" hint. After deploying the backend to a public URL, update `frontend/.env` `EXPO_PUBLIC_BACKEND_URL` to that URL and rebuild the APK. TypeScript clean.

### 2026-09-01 — Fix Lock, Splash, SMS, OAuth + Build
**Feature:** 5-request fix bundle + production APK rebuild
**Status:** Completed
**Summary:** Fixed PIN save failure via AsyncStorage fallback (`storage-service`), moved PIN setup into onboarding (now 4 steps), removed native splash screen (`Theme.App.SplashScreen` in `styles.xml` + `SplashScreen` calls in `_layout.tsx`), added SMS-to-party intent in `add-transaction.tsx` (`sms:` URL open), fixed production OAuth redirect (`credeasy://` literal instead of `Linking.createURL` which gave `exp://localhost`). TypeScript clean; `eas.json` `buildType` corrected to `apk`; local `gradlew` release build started.
**Operator follow-up (Supabase):** In the Supabase project dashboard, Authentication → URL Configuration → Redirect URLs, add `credeasy://` (the production deep-link scheme). Without this, Google sign-in from the production APK lands on `error=redirect_uri_mismatch`.

### 2026-09-01 — Fix Quoted Colors, Voice Sign-In, Post-Login Redirect
**Feature:** Color tokens, voice assistant auth UX, post-sign-in redirect
**Status:** Completed
**Summary:** Fixed widespread `'colors.X'` (string-quoted) → `colors.X` (object access) in styles and props across `app/login.tsx`, `app/onboarding.tsx`, `app/paywall.tsx`, `app/voice-assistant.tsx`, `src/components/TrialGate.tsx`. These were rendering as the literal string `"colors.primary"` (invalid CSS) and falling back to defaults — Continue buttons, plan cards, modals, and the input placeholder all looked broken. Voice assistant (`/voice-assistant`) now shows an inline sign-in card when the user is not authenticated (`authStatus !== 'authenticated'`); mic and text input are disabled. `login.tsx` now calls `markSetupDone()` after successful Google sign-in, so signing in from Settings no longer routes the user back to `/onboarding` on next launch. TypeScript clean; release APK rebuilt (49.8 MB).

### 2026-08-30 - OkCredit UI Reskin
**Feature:** OkCredit-style visual redesign
**Status:** Completed
**Summary:** Reskinned the entire app with an OkCredit-inspired UI: new OkCredit green palette (#1A8E3D), unified `src/utils/colors.ts` token file, redesigned home dashboard with clean top-bar layout, summary card, pill buttons; WhatsApp-style chat entry in add-transaction with big amount bubble; contact-picker in add-party using expo-contacts; all tabs and screens restyled with consistent border radius (14px), light gray bg (#F2F2F2), and green/red accent pills. All existing features (auth, storage, subscriptions, voice) untouched. TypeScript clean.

### 2026-08-31 - Play Store Production-Ready
**Feature:** Audit + production-readiness for Google Play Store
**Status:** Completed
**Summary:** Ran full codebase audit (tsc, eslint, pytest — all clean). Fixed `isPreviewFallbackAllowed` in `revenuecat.tsx` (removed `|| Platform.OS === 'web'`). Added `BasicBanner.tsx` platform shim resolving ESLint's import/no-unresolved on the ad component. Removed unused React import from `BasicBanner.web.tsx`. Removed unused `initialParties/Transactions/Bills` imports from `storage-service.ts`. Updated `app.json` with `versionCode`, `playStoreUrl`, `privacyPolicyUrl` (at root level), and cleaned `android.permissions` to only the five actually-used permissions. Updated `eas.json` production profile with `developmentClient: false` and `buildType: release`. Added a `signingConfigs.release` block (commented, with keytool instructions) to `build.gradle` and documented the signing requirement clearly. Updated `.gitignore` to block `*.jks` and `*.keystore` (except debug). Created `docs/PRIVACY-POLICY.md` with all required sections. Created `docs/PLAY-STORE-SETUP.md` with the complete step-by-step submission checklist including keystore generation, AdMob verification, RevenueCat product setup, Data Safety form, and EAS build commands. Cloud sync remains intentionally broken per project constraints.

### 2026-08-26 - Fixes Applied (Audit)
**Feature:** Code fixes from Fixing Guide audit
**Status:** Completed
**Summary:** Applied Part 5.3 sign-out fix in `frontend/src/lib/auth.tsx` — sign-out now pushes to cloud before clearing local data (throws if push fails). AdMob configured in `frontend/app.json` with Android/iOS app IDs. Database migration completed. Cloud sync remains intentionally broken per project constraints.
