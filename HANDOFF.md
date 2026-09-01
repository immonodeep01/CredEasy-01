# CredEasy - Feature Handoff Log

## Template
**Feature:** [Feature name]
**Status:** [Completed/In Progress/Blocked]
**Summary:** [1-2 sentences on what was done]

---

## Feature History

<!-- Add completed features below this line -->

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
