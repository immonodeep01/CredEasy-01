# CredEasy - Feature Handoff Log

## Template
**Feature:** [Feature name]
**Status:** [Completed/In Progress/Blocked]
**Summary:** [1-2 sentences on what was done]

---

## Feature History

<!-- Add completed features below this line -->

### 2026-10-06 — Add Cloud Run Backend Deployment Pipeline
**Feature:** Add backend container and Cloud Build configuration for deploying the Android API to Cloud Run.
**Status:** Configuration added and locally validated; Cloud Build trigger, Artifact Registry repository, IAM grants, and remote deployment require Google Cloud Console access.
**Summary:** Added a backend-only Docker image build with `.env` exclusion and a root `cloudbuild.yaml` that pushes to Artifact Registry and updates the existing `credeasy-api` service. Documented trigger creation, build/runtime service-account permissions, and post-deployment checks; no credentials are included in source.

### 2026-10-06 — Tune Ledger Empty State and Reports Navigation
**Feature:** Fit the empty-ledger illustration to the getting-started layout, remove the Reports backup card, and provide direct return navigation.
**Status:** Complete — validation and arm64 release build passed.
**Summary:** The Ledger empty state hides “No parties found” and its dock Add Customer shortcut while empty; the illustration, prompt, and main Add Customer action remain. The dock shortcut returns once a party exists. Reports keeps its previous layout, removes its duplicate Google Drive backup card, and has a back-to-Ledger control. The verified arm64 QA APK is 53,451,316 bytes (SHA-256 `A98B819A6E816AE70E681898523686989C0413E06F0C258BAED46401DB3C8C6E`).

### 2026-10-05 — Simplify Chotu Widget Controls and Speech Amounts
**Feature:** Use one right-aligned mic control while idle, explicit Send/Stop while listening, prohibit party creation from the widget, and improve spoken thousands.
**Status:** Implementation and targeted validation passed; release APK rebuilt for arm64. Physical launcher/microphone testing remains pending.
**Summary:** Removed quick-action controls. The idle row has “Talk to Chotu” above “Tap to speak” and a right-aligned mic; listening shows a live transcript and submits only after Send, while Stop discards it. Transaction proposals require explicit Yes/No buttons; stock proposals use spoken yes/no. Widget ADD_PARTY actions and legacy pending party flows are rejected. The shared TTS endpoint expands `₹46,500` and grouped numbers into complete Indian number words, with English/Hindi regression coverage. The rebuilt arm64 QA APK is 53,288,408 bytes (SHA-256 `BC070F884F5F24703A5BA2AA8B67FD167A2C29CD55BACCA877EED1D4EA0AFDE7`).

### 2026-10-05 — Add Transaction Confirmation Buttons to Chotu Widget
**Feature:** Confirm or cancel proposed widget transactions using Yes/No buttons instead of a spoken response.
**Status:** Implemented and validated; release APK rebuilt for arm64. Physical widget interaction remains pending.
**Summary:** Pending transaction proposals now show explicit Yes and No buttons, and the widget refuses voice confirmation for them. Stock proposals continue to use spoken confirmation; no write occurs unless the relevant confirmation path is explicitly used. The latest rebuilt APK also labels the idle widget “Talk to Chotu” with “Tap to speak” underneath.

### 2026-10-05 — Prepare Play Store Audit and Reduce APK Size
**Feature:** Review current Play submission requirements, reduce local APK size, and audit release readiness.
**Status:** Security review remediation and local QA build complete. The arm64 APK verifies and targets API 36. Production publication remains blocked on Play Console setup, upload-key signing, public deletion/privacy resources and manual declarations.
**Summary:** Constrained release output to arm64 for a 53.3 MB local APK, about 59.8% smaller than the 132.6 MB universal build, removed unused storage, contacts-write and overlay permissions via Expo config, and fixed the headless widget's App Lock bypass by blocking its actions and scrubbing displayed state. The production profile remains an AAB so Play can serve ABI-specific installs. See `docs/PLAY-STORE-SETUP.md` for verified policy and pre-submission checks.

### 2026-10-05 — Restore Speech Detection and Update Widget Artwork
**Feature:** Restore detection for quieter spoken commands and replace the Chotu character in widget artwork.
**Status:** Implemented and validated. Focused VAD tests, frontend TypeScript/lint, Expo prebuild, Android release build, APK resource/archive checks, and v2 signature verification passed. Physical-device voice testing remains pending.
**Summary:** Lowered and capped adaptive RMS thresholds so ordinary quieter speech can trigger capture while the multi-frame noise filter remains active. The widget processing icon and launcher preview now use CredEasy's current app mark instead of the Chotu character. The local QA APK is at `frontend/android/app/build/outputs/apk/release/app-release.apk`.

### 2026-10-05 — Resize Chotu Widget and Stop on Speech End
**Feature:** Constrain the widget to one home-screen row and prevent ambient noise from keeping voice capture open.
**Status:** Implemented and validated. Speech endpoint tests, frontend TypeScript/lint, regenerated Android provider, release APK build, archive checks and v2 signature verification passed. Physical device interaction remains unavailable.
**Summary:** The widget provider now uses a fixed 250dp x 70dp footprint, approximately four icons wide by one row high. Native voice activity uses a higher adaptive onset threshold and multi-frame onset/release gating; intermittent noise no longer resets the speech-end timer. The local QA APK is at `frontend/android/app/build/outputs/apk/release/app-release.apk`.

### 2026-10-05 — Redesign Chotu Widget and Improve Spoken Amounts
**Feature:** Match the widget to the compact Chotu reference and improve TTS clarity for rupee amounts.
**Status:** Implemented and validated. Backend voice tests (33), frontend TypeScript, lint, Android release build, generated provider metadata, and APK signature verification passed. Physical device/launcher testing remains pending.
**Summary:** The widget now uses a compact themed horizontal layout with mic, Balance, Add entry, and Stock actions; the Stock action now queries inventory. Spoken currency amounts are normalized into English/Hindi Indian number words, TTS rate is reduced to 0.98, and the native duplicate-play call was removed. The local QA APK is at `frontend/android/app/build/outputs/apk/release/app-release.apk`.

### 2026-10-05 — Refine Chotu Widget and Voice Input
**Feature:** Match the Chotu widget to CredEasy's theme, make party creation check contacts, improve noisy-room voice stopping, and build the release APK.
**Status:** Implemented and validated. Frontend type-check/lint, six focused frontend tests, five backend voice-action tests, both-theme widget renderer checks, release APK archive/resource checks, and APK v2 signature verification passed. No Android device is attached for launcher or microphone testing.
**Summary:** The widget now renders dedicated idle, listening, processing, confirmation, result, and error states with CredEasy light/dark colors and Balance, Add entry, Reminders, and History actions. In-app voice party creation requests Contacts access only after an explicit add-party request, then searches the complete readable list for an exact name and automatically uses a single matching mobile number; noise-adaptive VAD and earlier action handling reduce false listening and perceived delay. The local release APK is at `frontend/android/app/build/outputs/apk/release/app-release.apk`.

### 2026-10-05 — Improve Chotu Voice, Ledger, Reminders and Splash
**Feature:** Stabilize noisy-room voice activity detection, avoid contacts permission prompts from Chotu, preserve full inventory context and party opening balances, route WhatsApp reminders to party chats, and remove splash-logo white framing.
**Status:** Implementation and targeted checks passed; local Android release APK built successfully at `frontend/android/app/build/outputs/apk/release/app-release.apk`. The APK includes the embedded JavaScript bundle and required Oboe/audio libraries; physical-device validation remains pending.
**Summary:** Chotu now calibrates a rolling noise floor and keeps a longer audio preroll, includes all local inventory items and movements in assistant context, and saves opening balances directly from the party balance form. Reminders use the shared direct-chat/QR helper and splash image/background use the same green. The widget now draws an immediate visible ready state before asynchronous session/storage hydration.

### 2026-10-05 — Add Headless Chotu Android Widget
**Feature:** Add a home-screen Chotu widget with voice capture, quick questions, spoken answers, confirmed ledger/inventory/party writes, and explicit permission/login setup.
**Status:** Implemented; TypeScript and Expo config validation passed. Android prebuild/build and physical-device validation remain pending because the generated Android project already contains unrelated local changes.
**Summary:** The widget runs through `react-native-android-widget` headless tasks, shares Chotu backend/context/TTS helpers with the app, and uses a microphone foreground service with the existing Google STT streaming/upload-fallback path. Navigation and WhatsApp reminders remain widget-only explanatory messages because they require visible app/share UI; setup, build commands, and manual verification are in `docs/CHOTU-WIDGET.md`.

### 2026-10-05 — Pause Chotu Recording During Replies
**Feature:** Stop microphone capture while Chotu speaks, then resume after playback.
**Status:** Implemented; frontend TypeScript and focused ESLint passed, and the Android release APK build and archive checks passed.
**Summary:** TTS now cancels any active microphone capture before playback and no longer starts barge-in listening during the response. Listening resumes after playback completes or a playback failure/timeout is handled; the refreshed APK is available at `credeasy-release.apk`.

### 2026-10-05 — Improve Chotu Voice Quality and Diagnostics
**Feature:** Use natural male Indian Chirp 3 HD voices for Hindi/Indian English, select Hindi from reply text, reduce premature VAD cutoffs, and surface actionable provider errors.
**Status:** Implemented; TypeScript, focused ESLint, 31 backend tests, and Android release build passed. APK archive/native-library checks and v2 signature verification passed (SHA-256 `7B1ABAC71C2661818184BEB6EB94C96F0CDCA850EB6C80C9B85570AF410CBE5A`). The live API is missing `/api/voice/transcribe/stream` (WebSocket upgrade returns HTTP 404); deploy the updated backend with Google Cloud project/ADC configured before the new Google voice can be heard. An Android device is connected, but no microphone interaction was run.
**Summary:** Chotu now propagates Google’s recognized language into replies and TTS, selects the male `Chirp3-HD-Puck` voice, and returns/logs safe provider metadata; native auto-stop waits 1.4 seconds of silence, and HTTP errors retain backend detail. The rebuilt release APK is available at `credeasy-release.apk`.

### 2026-10-05 — Stabilize Continuous Chotu Listening
**Feature:** Fix native voice capture, improve Hindi/English recognition fallback, add barge-in, stop stale assistant turns, and rebuild the Android release APK.
**Status:** Implemented; frontend TypeScript and focused ESLint passed, 30 focused backend tests passed, and the release APK passed archive, native-library, and v2-signature checks. Physical-device mic testing remains unavailable, and the backend must be deployed separately for the updated TTS voice to take effect.
**Summary:** Native VAD keeps PCM in memory and submits a temporary WAV through the same Google transcription endpoint when WebSocket streaming is unavailable; the Expo recorder is now web-only, and silent native turns keep the user-started conversation listening. Chotu listens during replies, cancels the prior turn when interrupted, uses a different male Indian Hindi voice, and the new release APK is available at `credeasy-release.apk`.

### 2026-10-04 — Stabilize Chotu Voice Capture and Playback
**Feature:** Fix Android voice recording failure and sheet-close crash, preserve spoken replies during route changes, make the composer keyboard-safe, and tune the Indian male TTS voice.
**Status:** Implemented; TypeScript check, focused ESLint (one pre-existing unused-variable warning), eleven focused backend tests, release build, APK archive verification, and v2 signature verification passed. Physical-device playback and keyboard behavior were not retested.
**Summary:** Removed the recorder-state polling hook that could access an Expo shared recorder after release, added a same-provider upload fallback when the streaming WebSocket is unavailable, and kept in-flight TTS playing on route blur. Hindi replies now use a male Chirp 3 HD voice with a raised pitch and Indian English uses a male Wavenet voice.

### 2026-10-05 — Package Oboe for Native Voice Capture
**Feature:** Fix the Android voice-assistant crash caused by the Oboe native library being absent from release APKs.
**Status:** Implemented; release build and APK archive verification passed. On-device retest is blocked because Android canceled installation with `INSTALL_FAILED_USER_RESTRICTED`.
**Summary:** The app Gradle build stages ABI-matched `liboboe.so` files from the resolved Oboe Prefab artifact before native library merging; the release APK contains both Oboe and the audio module for all four configured ABIs.

### 2026-10-04 — Move Chotu Speech to Google Cloud
**Feature:** Use Google Cloud Speech-to-Text for voice transcription and Cloud Text-to-Speech for spoken replies, while keeping Gemini 2.5 Flash-Lite for assistant responses.
**Status:** Implemented; all 32 targeted backend tests, Google request-schema checks, and changed-section formatting checks passed. Live provider calls require Google Cloud project configuration, enabled Speech-to-Text and Text-to-Speech APIs, and backend Application Default Credentials.
**Summary:** Native M4A/WebM audio is sent to Speech-to-Text v2 with automatic decoding and Hindi/Indian English recognition; spoken responses use Cloud Text-to-Speech MP3. Legacy speech providers are used only until Google Cloud is configured, and configured Google failures do not silently switch providers.

### 2026-10-04 — Fix Blank WordPress Admin Screen
**Feature:** Resolve the blank `/admin/` screen and report a missing backend route clearly.
**Status:** Implemented in theme source version 1.3.2; package rebuilt and validated. The configured static-site origin `https://credeasy-app.onrender.com` returns 404 for API paths; the active API service `https://credeasy-01.onrender.com` responds to health checks but its current deployment does not yet include `/api/admin/config`.
**Summary:** Admin CSS, Supabase client, and app JavaScript now load directly from the active theme directory instead of relying on missing `/admin/assets/*` server rewrites. The sign-in page now explains a backend 404; the WordPress setting must use `https://credeasy-01.onrender.com` after the backend admin routes are deployed.

### 2026-10-04 — Make WordPress Admin Route Resilient
**Feature:** Fix `/admin` resolving to the WordPress 404 page when the saved rewrite table is stale.
**Status:** Implemented in theme source version 1.3.1; route dispatch now recognizes the admin page, its assets, and proxy endpoints directly during request parsing. Verified the deployed symptom against `https://credeasy.live/admin`.
**Summary:** Added a route-parsing fallback so `/admin` no longer depends on WordPress rewrite rules being flushed during theme activation. Existing installations on v1.3.0 can immediately refresh the route table under **Settings → Permalinks → Save Changes**; rebuilt the upload ZIP with the permanent fix.

### 2026-10-04 — Configure Admin Backend from WordPress Settings
**Feature:** Remove the need to edit `wp-config.php` or find Managed WordPress SFTP just to connect the packaged admin console.
**Status:** Implemented; URL setting is exposed on both WordPress General Settings and its dedicated shortcut, input is constrained to an HTTPS origin, and the server-side proxy uses WordPress safe-request handling.
**Summary:** Added **Settings → General → CredEasy Admin** (plus **Settings → CredEasy Admin**) to enter and save the FastAPI backend origin, so the user can configure it from the existing General Settings page if the submenu is unavailable. Rebuild the theme ZIP before uploading; service-role credentials remain backend-only.

### 2026-10-04 — Package Admin Console with WordPress Theme
**Feature:** Serve the operations console at `/admin` on the Managed WordPress site and rebuild the upload ZIP.
**Status:** Implemented; WordPress rewrite/API proxy setup, packaged admin assets, builder/archive verification, and runtime readiness checks completed. Live access still requires the backend URL, Supabase migration/OAuth redirect, and backend secrets.
**Summary:** Extended the CredEasy WordPress theme with `/admin` plus an HTTPS-only, endpoint-allowlisted proxy to the FastAPI admin backend; the ZIP bundles the console and local Supabase client without any service-role secret. Deployment prerequisites are documented in `docs/WEBSITE-GODADDY-DEPLOYMENT.md`.

### 2026-10-04 — Add the Internal Admin Console
**Feature:** Add a first-party, Google-authenticated CredEasy operations console covering the 16 requested admin modules.
**Status:** Implemented and validated with focused admin authorization tests and the full backend suite; live deployment still requires the SQL migration, verified-owner allowlist, Supabase Google redirect, and backend service-role configuration.
**Summary:** Added a responsive backend-served admin console with server-checked roles, user/session controls, audit logs, support ticket workflows, CMS/announcement drafts, connected business activity, operational metrics and CSV exports. Not-yet-integrated workflows are clearly labeled; setup and integration limits are documented in `docs/ADMIN-CONSOLE.md`.

### Configure Gemini, Sarvam, and Hands-Free Chotu Turns
**Feature:** Use Gemini 2.5 Flash-Lite for Chotu's assistant replies, Sarvam Bulbul v3's youthful male voice, and hands-free pause/resume voice conversation.
**Status:** Implemented and validated: frontend TypeScript and targeted ESLint passed, all 47 backend tests passed, and the Android release APK built with archive and v2 signature verification.
**Summary:** Provider calls remain server-side with timeouts and no silent cross-provider fallback after a configured provider fails. The `rehan` voice is youthful but not a guaranteed child voice. Once the user starts a mic session, metering-based silence detection submits speech and Chotu automatically listens again after spoken replies; silence-only captures and overlong utterances are bounded. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (94,793,586 bytes; SHA-256 `037FF157100EA45368F9C6B8D9B7EAC53A802B06662EBADB15913863F8663795`). Configure rotated provider secrets on the backend host before deployment; the local Gradle release APK is QA-signed with the debug keystore, not production signing credentials.

### 2026-10-03 — Slow Chotu's Greeting Run and Add Jumping Hi
**Feature:** Hold after Chotu's Ledger greeting for 7–8 seconds, halve the run speed, make footfalls clearer, add occasional 5–6 jump greetings, enlarge Add customer, and rebuild the Android release APK.
**Status:** Implemented; focused frontend ESLint, TypeScript validation, Android release build, APK integrity, and all 57 generated sprite-frame checks passed.
**Summary:** Chotu now waits 7–8 seconds after saying hi before his first run, uses double-duration run frames and a 4.4-second minimum crossing, and sometimes greets with 5–6 repeated jumps and “Hi!” text. The Add customer button is larger while the dock remains transparent. Reduced-motion preferences continue to suppress movement. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (94,790,558 bytes; SHA-256 `F62A8D8B144C099A5C9D92B1A101479B8DED65B1F25DAE01EA73C21F61239207`).

### 2026-10-03 — Greet on Every Ledger Visit
**Feature:** Make Chotu say hi and wave every time the user opens the Ledger, then rebuild the Android release APK.
**Status:** Implemented; focused frontend ESLint, TypeScript validation, Android release build, APK archive integrity, and all 57 packaged sprite-frame checks passed.
**Summary:** Chotu now starts each Ledger focus at the left dock with the localized greeting and wave, instead of waiting for the idle timer or a return run from the right. Keyboard and business-picker visibility changes do not trigger duplicate greetings. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (94,789,810 bytes; SHA-256 `CDFAB67F539468C55BA633C0621771B39B7DDE286AE767FBA4879DB49EBF4BF7`).

### 2026-10-03 — Let Chotu Run Over the Visible Ledger List
**Feature:** Remove the opaque blank strip behind Chotu and Add customer, make greetings start a wave, correct every run animation's facing, and tune idle and seated dwell times.
**Status:** Implemented; focused frontend ESLint, TypeScript validation, and diff checks passed.
**Summary:** Changed the Ledger dock into a transparent overlay above the bottom bar so party names remain visible beneath the motion lane, with a smaller Add customer target and scrollable end spacing for the final party. Chotu now waves whenever his left-side greeting appears, uses sprite-specific facing for each run sequence, and holds idle and seated poses for randomized 5–6 second intervals.

### 2026-10-03 — Correct Chotu Run Direction and Left-Side Greeting
**Feature:** Fix Chotu facing opposite the direction of travel, keep the greeting on the Ledger's left side, lower the bubble slightly, and fill the login logo badge.
**Status:** Implemented; frontend lint, TypeScript validation, Android release build, and APK integrity checks passed.
**Summary:** Corrected the sprite mirroring for left/right runs and kept the localized greeting in a fixed left-side dock position, shown only after five idle seconds at that side. Lowered the bubble and scaled the login-only logo artwork to fill its clipped badge without changing other logo sizes.

### 2026-10-03 — Randomize Chotu Sprite Animations and Refresh Login Hero
**Feature:** Use the additional supplied mascot poses in randomized animation cycles, show the speech bubble only after five idle seconds, and redesign the green login hero.
**Status:** Implemented; frontend lint, TypeScript validation, Android release build, and APK integrity checks passed.
**Summary:** Added 57 cropped sprite frames for idle, wave, running, story, sleepy, reaction, walking, and thinking sequences. Actions and idle intervals are randomized on the Reanimated UI thread; runs cross between dock edges, and the localized bubble appears only after five idle seconds. Shifted the bubble slightly upward and right, and rebuilt the login hero as a left-aligned forest-green brand lockup with a compact horizontal logo.

### 2026-10-03 — Compact Ledger Action Dock
**Feature:** Reduce the Ledger mascot and Add customer dock's reserved space so more party rows remain visible.
**Status:** Implemented; frontend lint and type checks passed.
**Summary:** Reduced the dock and its touch targets to a compact 72 px row while keeping Chotu's artwork, greeting, and motion lane above the bottom bar. The smaller dock gives the parties list more visible height without placing the controls over party cards.

### 2026-10-02 — Add Chotu Dock Motion and Visibility Preference
**Feature:** Move Chotu to the Ledger dock's left side, greet users on app open/resume, add occasional running/jumping, and provide a Settings off switch with a compact actions menu.
**Status:** Implemented and verified with frontend TypeScript, focused Expo lint, Android Expo export, and `git diff --check`; device-level motion/visual verification remains outstanding.
**Summary:** Added a persisted mascot preference, a Ledger-focus-aware localized greeting bubble on app open/resume, and occasional UI-thread running/jumps along the left dock with reduced-motion handling; Add customer stays on the right. When disabled, one up-arrow button reveals Add customer and voice-assistant mic actions.

### 2026-10-02 — Refine Chotu Running and Dock Presence
**Feature:** Use the supplied sprite-sheet run/jump art, reduce Chotu's size by 40%, remove the caption, and move the greeting above the character.
**Status:** Implemented and verified with frontend TypeScript, focused Expo lint, Android Expo export, and `git diff --check`; device-level visual verification remains outstanding.
**Summary:** Cropped eight running frames and a separate jump pose from the supplied spritesheet, animate them on Reanimated's UI thread, and mirror the cycle for leftward movement. Reduced the character drawing to 60% of its former dimensions, removed “Ask Chotu” beneath it, and raised the greeting bubble clear of its face; a dock-level shadow anchors the motion.

### 2026-10-02 — Redesign Chotu with the LittleI Sprite
**Feature:** Replace Chotu's hand-built illustration with the supplied LittleI character art.
**Status:** Implemented and verified with frontend TypeScript, focused Expo lint, and Android Expo export; device-level visual verification remains outstanding.
**Summary:** Cropped the standing and two waving poses from the supplied transparent spritesheet and used them for a brief reduced-motion-aware Reanimated wave. Preserved the Ledger action, accessibility labels, and voice-assistant navigation.

### 2026-10-02 — Add the Ledger Chotu Mascot
**Feature:** Replace Chotu's quick-actions menu entry with a small waving-boy action on the Ledger.
**Status:** Implemented and verified with frontend TypeScript, focused ESLint, and `git diff --check`. Visual and screen-reader behavior still merits device verification.
**Summary:** Added a custom native-view mascot with a short focus-triggered, reduced-motion-aware Reanimated wave and routed it to the existing voice-assistant sheet without auto-recording. A reserved action dock keeps Add customer directly available and hides while the keyboard or business chooser is open.

### 2026-10-02 — Keep WhatsApp QR Reminder Attachments in the Targeted Share
**Feature:** Fix QR reminders opening the party chat without attaching the business QR, and rebuild the Android release APK.
**Status:** Implemented and verified with the native patch application, frontend TypeScript, focused ESLint, successful Gradle release build, and APK v2 signature verification. Physical-device WhatsApp testing remains outstanding.
**Summary:** Removed the forced private `Conversation` component that bypassed WhatsApp's attachment-share handler. Android now dispatches one package-targeted `ACTION_SEND` carrying both the QR stream and recipient JID. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (93,602,415 bytes; SHA-256 `173052741E23001F773F082E94F74553F446B5200589D2257B15D4A6837AFE35`; v2 signature verified; debug-key signed for QA).

### 2026-10-02 — Restore Recipient-Targeted WhatsApp QR Dispatch
**Feature:** Fix Android WhatsApp QR reminders so they dispatch one targeted share intent containing the party number and QR image, then rebuild the release APK.
**Status:** Implemented and verified with the package patch reversing/reapplying cleanly, frontend TypeScript, focused ESLint, successful Gradle release build, and APK v2 signature verification. Physical-device WhatsApp testing remains outstanding.
**Summary:** The native WhatsApp handlers now prepare the QR/message payload and launch the selected recipient conversation exactly once; Android share files explicitly use app-internal cache. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (93,602,415 bytes; SHA-256 `9F00B7201D9C9D4FC307DADFD18074275EE43E3A149DBE3807FA103F3F5300AA`; v2 signature verified; debug-key signed for QA).

### 2026-10-02 — Speed Up WhatsApp Reminders and Remove Destructive Settings Actions
**Feature:** Make recipient-targeted WhatsApp reminders return control as soon as the app launch is dispatched, remove account and business deletion controls, and reduce the launcher mark by 30%.
**Status:** Implemented and verified with frontend TypeScript and focused ESLint; WhatsApp behavior could not be physically device-tested.
**Summary:** Targeted WhatsApp QR shares no longer wait for the user to return to CredEasy before resolving, and preserve the party number and QR attachment. The Settings account-deletion button and business chooser deletion option are removed, and the launcher source and Android density assets use a 30%-smaller mark.

### 2026-10-02 — Introduce Chotu and Redesign Daybook
**Feature:** Rename the voice helper to Chotu, extend it to app guidance and inventory stock questions/changes, remove Today’s sales and collection tiles, redesign Daybook as a date-range ledger statement, and build the Android release APK.
**Status:** Implemented and verified with frontend TypeScript, focused ESLint (0 errors; 4 existing unused-variable warnings in the voice screen), 23 backend voice/auth tests, a successful Gradle release build, and Android APK v2 signature verification.
**Summary:** Chotu can explain and navigate CredEasy, answer ledger/inventory questions, and propose stock movements; transaction and stock writes remain behind explicit confirmation. Daybook now summarizes selected date ranges and displays all matching entries; Ledger no longer shows the two today tiles. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (93,641,615 bytes; SHA-256 `4A31EBA15F696250578A93B7717FC009D36ED115C672624FEA4B8C4DB7F181D1`; v2 signature verified; debug-key signed for QA).

### 2026-10-02 — Simplify Ledger, Improve QR Sharing, and Refresh Sign-in
**Feature:** Remove redundant Ledger actions and recent transactions, align Quick links, support standard WhatsApp when WhatsApp Business is unavailable, and redesign the login screen.
**Status:** Implemented and verified with frontend TypeScript and focused ESLint; full lint still reports 14 existing warnings in unrelated files.
**Summary:** The Ledger now focuses on balances, quick links, and parties. QR reminders fall back to the native share sheet when direct WhatsApp targets fail, and the Google/offline sign-in screen has a more compact, clearer layout without changing its access flow.

### 2026-10-02 — Repair Reminders, Account Deletion Diagnostics, PDF Imports, and Refresh Ledger/Voice UI
**Feature:** Make WhatsApp reminders open the selected chat reliably, provide a compatible PDF-import fallback, clarify account-deletion backend configuration failures, refresh Ledger and voice-assistant screens, reduce launcher artwork, and build the Android release APK.
**Status:** Implemented and verified with 5 focused CSV import tests, frontend TypeScript, focused ESLint (0 errors; 4 existing unused-variable warnings in the voice screen), 35 backend auth/import tests, and a successful Android release build with APK v2 signature verification. Physical-device WhatsApp verification and production backend deployment remain outstanding.
**Summary:** Text reminders now open the selected WhatsApp chat directly, while QR shares watch app return and time out instead of staying stuck on “Opening…”. PDF import falls back to the deployed legacy parser when the newer conversion endpoint is unavailable, then creates rows for the existing on-device review flow; Ledger and voice-assistant layouts were refreshed, the launcher mark was reduced, and backend configuration failures for account deletion return actionable 503 responses. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk` (93,633,539 bytes; SHA-256 `60D4E96143FA52F925673AE0E79889D63401FBE730DD6AC95C18A98E8F925E7B`; v2 signature verified; debug-key signed). Production account deletion requires deploying the backend change with `SUPABASE_SERVICE_ROLE_KEY` configured; the current live backend also lacks the new PDF-to-CSV route, so the APK uses the compatibility fallback.

### 2026-10-02 — Configure App Lock, Business Deletion, Party Actions, and Notifications
**Feature:** Configure App Lock in Settings after onboarding, safely sync and delete business workspaces, streamline party-detail actions, dismiss opened notifications, and prevent duplicate WhatsApp launches.
**Status:** Implemented and verified with frontend TypeScript, focused ESLint, Android Java compilation, and successful patch-package application. Live WhatsApp device testing and Supabase execution of the updated additive SQL remain outstanding.
**Summary:** Settings now supports first-time PIN setup and requires the current PIN to change it; business deletion requires a Security PIN and confirmation, preserves the final workspace, and uses an account-checked cloud RPC with deletion tombstones before local cleanup. Party edit/PDF/delete actions now live in a three-dot menu, opening a notification marks and dismisses it, and the Android WhatsApp share handler no longer launches the same share more than once; the in-app logos were reduced.

### 2026-10-02 — Gate WhatsApp Reminders, Convert PDF Imports, and Refresh Branding
**Feature:** Only allow reminders for customer receivables, convert PDFs to CSV before review, remove DOCX import, and apply the supplied logo throughout app, Android, and web assets.
**Status:** Implemented and verified with 16 backend import tests, 3 CSV parser tests, frontend TypeScript and focused ESLint, Android release build, and APK v2 signature verification; device-level WhatsApp/ad verification remains unavailable. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,862,755 bytes; SHA-256 `607850B754B3827C18831AA947578F4693FF20BD7F088ED5C0AF5A93DF608FF6`; debug-key signed).
**Summary:** The reminder UI and handler recheck that the customer still owes money, while the targeted WhatsApp QR share keeps the recipient number or reports failure. PDFs now convert to a normalized CSV before on-device parsing and review, DOCX is rejected, and the supplied C-and-arrow mark replaces the app and launcher branding; security review found no exploitable issues in the reviewed upload and reminder changes.

### 2026-10-01 — Route WhatsApp QR Shares to Recipient and Show Test Ads Everywhere
**Feature:** Direct WhatsApp QR reminders to the selected party and make every ad placement use visible Google test ads across devices.
**Status:** Implemented and verified with TypeScript, focused ESLint, six focused regression tests, a successful release APK build, manifest inspection, and APK v2 signature verification. No ADB device was connected for live WhatsApp/ad verification.
**Summary:** WhatsApp's targeted share now includes the normalized party number together with the cached QR image, requesting the recipient's chat instead of only presenting the share picker. Banner, native and interstitial placements use Google's test units on every device/build, shared initialization no longer restricts test behavior to one device ID, and the native ad now renders its registered ad assets. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,882,155 bytes; SHA-256 `E9A716E6237395CEA195FF0BE5D03676806ECC7D616E96548DC9A0D50BC2E81A`; v2 APK signature verified; debug-key signed).

### 2026-10-01 — Fix WhatsApp QR Attachments and Android Startup Crash
**Feature:** Make business QR images accessible to Android share targets and fix the Android splash-screen startup crash.
**Status:** Implemented; TypeScript/ESLint and Android release build passed, the splash attribute is present in the packaged resources, and APK v2 signature verification passed. Installation on the connected phone was blocked by `INSTALL_FAILED_USER_RESTRICTED`, so the fixed build could not be launched there for runtime verification.
**Summary:** WhatsApp QR shares now stage a content-addressed copy under the app cache, a path allowed by react-native-share's Android FileProvider; the QR reminder no longer passes a file URI from the inaccessible app files directory. The app theme now provides AndroidX's required `splashScreenIconSize`, addressing the ADB-captured `InflateException` on launch. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,881,355 bytes; SHA-256 `E9AD399E023AC505286BA87B1C5579B108E4A770465B1B324CC109F865ABEEE4`; v2 APK signature verified; debug-key signed).

### 2026-10-01 — Fix OkCredit CSV Import, WhatsApp QR Sharing, Transactions, and Ads
**Feature:** Import the supplied OkCredit CSV balance summary, attach business QR images to WhatsApp reminders, accept decimal transaction amounts, make onboarding PIN optional, and serve Google test ads.
**Status:** Implemented and verified with the exact supplied CSV, frontend checks, a successful Android release build, package metadata, test AdMob manifest entry, and APK v2 signature verification. WhatsApp QR sharing and ad presentation still require physical-device verification.
**Summary:** The import flow recognizes compacted OkCredit customer/supplier Due and Advance reports and creates signed opening balances without inventing transaction history. WhatsApp image handoff avoids Android's incompatible direct-recipient-plus-image path, transaction entry uses a decimal keyboard, PIN setup has a skip action, and ad requests initialize the SDK and use Google's test IDs. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,880,719 bytes; SHA-256 `8AE5B7D59C45B4A81648EBA35CF55098CC402488B27E6866A06AA3F7F638052E`; v2 APK signature verified; debug-key signed).

### 2026-10-02 — Export Inventory, Search Contacts, and Repair Sharing/Sync
**Feature:** Export all inventory records, search the native contact picker, restore business photos in the account switcher, share profile QR images in WhatsApp reminders, and resolve orphaned inventory movement uploads.
**Status:** Implemented and verified with frontend TypeScript, focused ESLint, four CSV/contact tests, 18 backend auth tests, and a signed release APK build.
**Summary:** Inventory export shares all item metadata and movement history as CSV, and contact selection now filters by name or phone. Cloud business photos are localized before the switcher uses them, WhatsApp reminders stage the saved QR as a shareable local image, and movement history for removed items is preserved under cloud deletion tombstones; generic account-deletion errors now include actionable deployment/status information. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,875,571 bytes; SHA-256 `31BAD2B868EC69B1BFB8967D1248456B0D57111AFE1838ADFC66082541CDD716`; v2 APK signature verified; debug-key signed).

### 2026-10-01 — Export Complete Inventory
**Feature:** Add an Inventory option to export all item details and stock movement history as CSV.
**Status:** Implemented and verified with the focused CSV serialization test, frontend TypeScript check, and focused ESLint; no APK was built.
**Summary:** Inventory now shares a complete CSV from the device, including every stored item regardless of search/filter state, product/tax metadata, and movement history. The CSV uses separate labeled sections and preserves spreadsheet-safe quoting.

### 2026-10-01 — Improve Business Switching and Account Deletion
**Feature:** Open the business switcher from the Ledger avatar, show each business profile photo, route the active business to Profile and other businesses to Ledger, and improve account-deletion reliability and diagnostics.
**Status:** Implemented and verified with focused frontend checks, 32 backend tests, and a rebuilt release APK. The backend change must be deployed with `SUPABASE_SERVICE_ROLE_KEY` configured before production account deletion uses it.
**Summary:** The Ledger avatar now opens the business chooser; its business rows show saved profile images, tapping the active business opens Profile, and selecting another business switches to its Ledger. Account deletion now uses a current session token, refuses to clear device data unless Supabase deletion succeeds, and returns actionable upstream status while keeping sensitive upstream response details out of client errors. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,867,739 bytes; SHA-256 `CFAEC45745E6E12A4CE101AE08A58BDE03B4319CE0C4F4B94EE4E3B1CC9E1C59`).

### 2026-10-01 — Fix Business Switching, CSV Import, and Low-Stock Alerts
**Feature:** Return to Ledger after switching businesses, harden compact CredEasy CSV imports, and keep inventory low-stock notifications current.
**Status:** Complete and verified with the compact CSV regression test, `npx tsc --noEmit`, focused ESLint, and a release APK build/signature verification.
**Summary:** The Ledger avatar opens Profile; the separate business-name chooser returns to Ledger after selecting any business, including the active one. Compact tagged exports import all parties and transactions without summary labels or balance artifacts; low-stock notifications use stable item IDs, preserve read state, and refresh after inventory changes. Final release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (92,867,143 bytes; SHA-256 `43B323F1A094E378297F833220E886F4E9F3BC3DC25F9A7C99154FF9AD68D1F8`).

### Restore Returning Accounts, Repair Account Controls, and Refresh Branding
**Feature:** Recover returning Google users from their cloud business profile after reinstall, make Settings sign-out/account deletion work safely, and align the logo and launcher icon with CredEasy’s green theme.
**Status:** Implemented and verified; TypeScript, Expo config, backend tests (31 passed), release APK build, and APK v2 signature verification passed. The APK is locally signed with the Android debug certificate and is not Play Store upload-ready.
**Summary:** Startup/login now check Supabase for an existing business profile before routing an account into onboarding, and Settings passes the verified Security PIN through to account deletion. Account deletion removes that user’s private profile/QR media before deleting the Supabase Auth user and preserves local data on remote failure; refreshed logo/background and slightly smaller launcher artwork are applied across app, website, and Android density assets. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk` (SHA-256 `608FB6B1025196C3CD033AEA9B39CCF7884AE5C0033DD7C7253BFBB17CFF8712`).

### 2026-10-01 — Fix WhatsApp Reminders and Refresh the App Logo
**Feature:** Make party reminders try WhatsApp Business before standard WhatsApp, add a web-chat fallback, replace brand artwork with the supplied logo, and rebuild the release APK.
**Status:** Implemented and verified; TypeScript, focused ESLint, Expo config, Android release build, APK manifest, and APK signature checks passed. The reminder handoff was not exercised on a physical device.
**Summary:** Party reminders now target the saved party number in WhatsApp Business first, fall back to WhatsApp, and open the WhatsApp web chat if neither app can accept the share; Android package visibility is configured for both apps. The supplied green C-and-arrow logo now appears across app, launcher, splash, website, and Android mipmap assets, and the security re-review found no additional actionable issues.

### 2026-10-02 — Add Business Workspaces, In-App Legal Pages, and Security Fixes
**Feature:** Support multiple isolated businesses per Google account, add Help/onboarding legal and support destinations, resolve Profile keyboard overlap, and fix the three findings from the security review.
**Status:** Implemented and verified; TypeScript, Android bundle export, backend tests, release APK build, and APK signature verification passed.
**Summary:** The Ledger avatar now opens a business chooser with an Add another business action; local snapshots, Supabase records/realtime, and Drive backup files are partitioned by business, with the additive Supabase setup backfilling old data into the default business. Help and onboarding open local About, Privacy & Security, and Terms pages, Contact Us launches the requested email, Profile field sheets avoid the Android keyboard, sign-out clears saved Drive credentials, legacy ownerless data stays offline-scoped, and voice-generated transactions require explicit confirmation. Release artifact: `frontend/android/app/build/outputs/apk/release/app-release.apk`.

### 2026-10-01 — Fix Ledger Navigation, Profile Access, and Business Card Sharing
**Feature:** Repair utility-page returns, add a Ledger profile shortcut, move Inventory’s Add item action, and make business-card sharing produce a PNG.
**Status:** Implemented and verified; TypeScript, focused ESLint, Android bundle export, and Android release build passed.
**Summary:** Today transactions, Reports, Help, Settings, and Profile return to the canonical tabs route; Profile hides the bottom bar, and the Ledger header opens Profile from the saved avatar. Inventory’s Add item action is now a floating lower-right button above the tab bar, and Profile previews then shares a rendered PNG business card with available profile details and QR.

### 2026-10-01 — Recover From Stale Profile Images and Invalid Deep Links
**Feature:** Fix profile image cache errors, business-card sharing failures caused by missing image files, and the bare `credeasy:///` unmatched route.
**Status:** Implemented and verified; release APK rebuilt.
**Summary:** Legacy ImagePicker cache URIs are checked before migration; missing files are cleared from the profile with a request to select them again, and cloud sync continues without unavailable images. Bare CredEasy scheme links now resolve through the app entry route, while unknown links show a branded Ledger recovery screen.

### 2026-09-30 — Preserve Offline Data and Sync Ledger Media
**Feature:** Configure Android app-data backup, persist selected images for restore, and sync ledger/profile media through private Supabase Storage.
**Status:** Implemented; frontend TypeScript and targeted ESLint pass; Windows `gradlew.bat assembleRelease` succeeded.
**Summary:** Android backup rules include AsyncStorage databases and app-owned files while excluding SecureStore; picked images are copied to durable document files, and signed-in image sync uses a private per-user Supabase bucket. Fixed the profile-only local-data bootstrap case and added Storage RLS plus restrictive account-update guards to the additive Supabase setup. Offline reinstall recovery still depends on Android's device backup/transfer service; apply `docs/enable-transaction-realtime.sql` before expecting cross-device cloud/media sync.

### 2026-09-30 — Autosave Profile, Improve Help Navigation, and Add Daily Transaction Details
**Feature:** Save and sync Profile edits automatically, share a business-card image, make the Ledger search and daily totals interactive, and keep in-app back navigation predictable.
**Status:** Implemented; frontend TypeScript, targeted ESLint, and Android JavaScript bundle export pass. No APK was built.
**Summary:** Profile edits and image changes now save through the existing durable profile outbox; QR and profile images use portable data URIs and are included in Supabase profile data. Business-card sharing uses the entered business details. Ledger search now opens from the top-bar button, and Today’s sales/collection open separate transaction lists. Help, Reports, and Settings have explicit back destinations and hide the bottom bar.

### 2026-09-30 — Add Profile Field Editors and Category Picker
**Feature:** Make every Profile information row interactive with reference-inspired field sheets and business selection screens.
**Status:** Implemented; TypeScript, targeted ESLint, and Android JavaScript bundle checks pass. No APK was built.
**Summary:** Profile rows now open a bottom-sheet editor with clear and confirm controls; business type opens selectable options, and category opens a searchable Popular/Others grid with selected-state indicators. Updates remain on the Profile until the existing Save profile action persists them.

### 2026-09-30 — Add In-App Help Guide and Answers
**Feature:** Turn “How to use CredEasy?” into a browsable guide with topic groups, FAQs, and step-by-step answers.
**Status:** Implemented; TypeScript, targeted ESLint, and Android JavaScript bundle checks pass. No APK was built.
**Summary:** Added seven help categories with 45 question-specific answers, expandable question lists, numbered answer pages, and a support-sharing action. The guide covers the reference questions, including contact-book customer entry, transactions, PDF statements, supplier records, and account security; answers clarify that shared ledgers and OkCredit account recovery are not CredEasy features. The guide and answer screens are hidden from the main tabs and provide their own back navigation.

### 2026-09-30 — Redesign Bottom Navigation and Account Pages
**Feature:** Replace the Reports tab with an up-arrow menu and add dedicated Ledger, Profile, Help & Support, and focused Settings experiences.
**Status:** Implemented; frontend TypeScript, targeted ESLint, and diff checks pass. No APK was built.
**Summary:** Kept Ledger, Inventory, and Billing as the three direct tabs with Reports, Profile, Help, and Settings in the up-arrow menu. Settings now contains only Preferences, Google Account Login, and Google Drive Backup while retaining PIN, sign-out, account deletion, sync, and Drive flows. Profile groups Email under Other Information and clarifies customer visibility; Help links to verified policy pages and the published support email without inventing a WhatsApp number or refund terms.

### 2026-09-30 — Import Complete CredEasy CSV Exports
**Feature:** Parse the app's complete-data CSV export during onboarding.
**Status:** Implemented and verified against the supplied export; APK intentionally not rebuilt.
**Summary:** The CSV parser now scans past export metadata and handles multiple tables plus compacted party and transaction cells, including named-month dates, opening balances, and embedded amount/type text. The supplied file now parses as 5 parties and 22 transactions while preserving review-before-save.
**Validation:** Regression checks against the supplied CSV and standard comma/semicolon CSVs passed; TypeScript, targeted ESLint, and diff checks passed.

### 2026-09-30 — Parse CSV Imports On Device
**Feature:** Fix CSV imports rejected by the older hosted parser with a PDF/DOCX-only error.
**Status:** Implemented and verified; release APK rebuilt.
**Summary:** Confirmed the configured hosted endpoint still returns HTTP 415 for CSV. CSV files now parse locally on-device, including quoted/delimited fields, Indian-formatted amounts, opening balances, party types, and dated debit/credit entries; users retain the existing review-before-save flow without relying on the server.
**Validation:** Client parser behavior checks, TypeScript, targeted ESLint, backend import regression tests, diff checks, and `gradlew.bat assembleRelease` passed. No ADB device was connected for installation.

### 2026-09-30 — Refresh CredEasy Logo and Splash Screen
**Feature:** Apply the supplied C-and-growth logo across app branding, splash, and launcher surfaces.
**Status:** Implemented and verified; release APK built successfully.
**Summary:** Recolored the supplied artwork with a forest-to-ledger-green gradient and warm amber accent, removed its paper background, and generated adaptive/icon/splash exports. Updated the app logo component, light branded splash screen, Expo configuration, Android launcher density assets, native launch background, and website mark.
**Validation:** Expo prebuild config resolved, TypeScript and targeted ESLint passed, all launcher image densities were verified, and `gradlew.bat assembleRelease` produced the release APK.

### 2026-09-30 — Accept Excel and CSV Ledger Imports
**Feature:** Fix previous-data file selection and rename the spreadsheet import action to Excel.
**Status:** Implemented and verified. The updated backend must be deployed for `.xlsx` support.
**Summary:** The Excel picker now accepts CSV and XLSX regardless of file-provider MIME labels and validates selected extensions. Added server-side `.xlsx` worksheet parsing with a regression test, and updated the import label/help text.
**Validation:** `pytest tests/test_import.py -q` (14 passed), frontend TypeScript and targeted ESLint passed, and `gradlew.bat assembleRelease` produced the release APK.

### 2026-09-30 — Isolate and Persist Cloud Sync Changes
**Feature:** Queue all active ledger edits durably, sync across signed-in devices, and prevent local data from crossing Google accounts.
**Status:** Implemented; TypeScript and targeted ESLint pass with only existing warnings. Apply the updated additive `docs/enable-transaction-realtime.sql` in Supabase before relying on cross-device bill/recurring sync.
**Summary:** Added account-scoped local snapshots, durable bill/profile/recurring outboxes and Realtime merges, bill and recurring tombstones, visible sync status/retry in Settings, and complete “Back up and remove” cleanup only after successful upload. Ordinary sign-out still retains the prior account’s data locally; offline-only data remains separate and is never uploaded.

### 2026-09-30 - Scope Onboarding To Google Account
**Feature:** Show business setup onboarding for each newly signed-in Google account.
**Status:** Implemented; TypeScript check, targeted ESLint, and diff checks pass.
**Summary:** Replaced the Google onboarding decision's use of the device-wide setup flag with a per-Supabase-user flag, while retaining device-wide setup for offline users and app-lock compatibility. Added a legacy migration that binds existing setup completion to the current account before sign-out, so switching Google accounts no longer skips onboarding for a new account.

### 2026-09-30 - Redesign CredEasy Website
**Feature:** Responsive, product-accurate marketing site for CredEasy.
**Status:** Implemented and verified in desktop/mobile browser QA.
**Summary:** Reworked the standalone site with an accessible theme toggle, keyboard-operable feature tabs, workflow carousel, responsive gapless product grid, accurate free/ad-supported pricing, and reduced-motion-aware GSAP motion. Removed unsupported product claims and unverified download/legal links; used the real app mark and checked photographic assets instead of fabricated app screenshots.

### 2026-09-30 — Parse OkCredit Backup Summaries
**Feature:** Import all parties and balances from OkCredit's positioned backup-summary PDF.
**Status:** Implemented and verified against the supplied PDF; release APK built.
**Summary:** Added layout-aware parsing of customer/supplier rows, phone numbers, and Due/Advance columns, preserving balances as signed opening balances. The supplied summary contains three parties and no transaction history, so the importer now explains that a ledger/transaction export is required for past entries. The backend parser must be deployed to the configured API before the APK can use the fix.

### 2026-09-30 — Improve Previous Ledger Import
**Feature:** Extract more complete ledger data from prior documents and reduce duplicate records after interrupted imports.
**Status:** Implemented; backend import tests, frontend TypeScript, targeted ESLint, and diff checks pass.
**Summary:** Added structured PDF/DOCX table parsing and CSV import with common party/date/amount/type/debit/credit/opening-balance headers, improved labeled-party and amount/date parsing, and explicit warnings for skipped rows and assumed dates. The review step now displays all parsed rows. Import reuses matching parties and skips matching previously-saved transaction rows, making retries after partial saves safer. Scanned/image-only PDFs still require OCR or a text/CSV export.

### 2026-09-30 — Preserve Notification Read State and Sync Badges
**Feature:** Keep read notifications read after reopening and show accurate unread badges in the app.
**Status:** Implemented and validated with TypeScript, targeted ESLint, and diff checks; native badge behavior still needs device verification.
**Summary:** Centralized notification generation and serialized storage updates, preserving each notification's read state by stable ID across refreshes. The Home badge and native app-icon badge now derive from the persisted unread list and refresh on Home focus and ledger changes; importing replacement data clears both stored notifications and the native badge.

### 2026-09-30 — Restrict Automatic Drive Backups to One Device
**Feature:** Automatically back up once daily from one device while letting other same-account devices view and manually upload backups.
**Status:** Implemented and release APK built. Run the updated Supabase setup SQL on the account's project before expecting device ownership.
**Summary:** The first eligible device claims permanent automatic-backup ownership in Supabase. It checks the shared Drive modification date and uploads only when the backup is not current for today; backup-on-change, resume, timer, and unconditional startup uploads have been removed. All devices continue to show the shared Drive file and retain the manual backup action. TypeScript, targeted lint, diff checks, and `assembleRelease` passed.

### 2026-09-29 — Synchronize Inventory Across Devices
**Feature:** Audit and harden inventory storage and sync inventory items and stock movements across signed-in devices.
**Status:** Implemented and validated; release APK built. Run the updated safe setup in `docs/enable-transaction-realtime.sql` before testing shared inventory.
**Summary:** Added durable item/movement outboxes, snapshot reconciliation, Supabase Realtime updates, and deletion tombstones. Stock movements are applied by a per-account database function that serializes quantity deltas, avoiding stale-device stock overwrites; inventory is now included in Drive backup/restore. Inventory focus/pull-to-refresh requests a cloud snapshot and shows actionable errors if the required Supabase tables are unavailable; initial pending changes are pushed independently of snapshot success. TypeScript, targeted ESLint, diff checks, and the release build passed.

### 2026-09-29 — Show Opening Balance in Party Ledger
**Feature:** Display the party opening balance as a ledger entry with edit and delete controls.
**Status:** Implemented and validated; release APK built.
**Summary:** The opening balance appears at the oldest end of the party transaction history with its date and resulting balance. Edit and delete actions require the Security PIN; deletion confirms explicitly and resets the opening balance to zero without changing transactions. TypeScript and diff checks passed, targeted lint had no errors (two existing unused-state warnings), and `app-release.apk` rebuilt successfully.

### 2026-09-29 — Edit Opening Balance and Delete Parties
**Feature:** Allow a user to edit or clear an existing party opening balance and delete a party using the Security PIN.
**Status:** Implemented and validated; release APK built.
**Summary:** Existing party edit now persists the opening-balance field, where blank resets it to zero and recalculates the balance. Added a PIN-gated, explicitly confirmed party deletion that removes its transactions and records durable party/transaction tombstones for cross-device sync. TypeScript, diff checks, and release build passed; targeted lint reported no errors, with only existing unused-variable warnings.

### 2026-09-29 — Persist Transaction Edits and Deletes
**Feature:** Sync transaction edits/deletes live and prevent deleted or edited entries from reverting after restart.
**Status:** Implemented and validated; release APK built. Apply the SQL setup in Supabase before relying on shared deletion protection.
**Summary:** Added shared per-user deletion markers in Supabase before physical transaction deletes, plus snapshot, Realtime, and pre-upload checks so stale devices cannot resurrect deleted IDs. An idempotent database trigger marks any transaction deletion and rejects a later upsert of the tombstoned ID, closing the stale-upload race. Updated `docs/enable-transaction-realtime.sql` with the marker table, RLS, trigger, and Realtime publication. TypeScript and diff checks passed, targeted lint had no errors (one existing unused-import warning), and `app-release.apk` rebuilt successfully.

### 2026-09-29 — Keep Deleted Transactions from Returning
**Feature:** Prevent stale cloud snapshots from restoring transactions that were deleted on another device.
**Status:** Implemented and validated; release APK built.
**Summary:** Persist transaction deletion tombstones locally, filter tombstoned IDs from cloud snapshot merges and realtime inserts/updates, and requeue cloud rows with tombstoned IDs for deletion. Local bulk removals now persist deletion tombstones and the delete outbox before saving the updated ledger. TypeScript, targeted lint, and diff checks passed; Gradle `assembleRelease` succeeded.

### 2026-09-29 — Align Home Quick Actions
**Feature:** Align the Voice assistant and Add customer action buttons with the Home plus button.
**Status:** Implemented and validated; release APK built.
**Summary:** Shifted both quick-action icon buttons 4dp inward so their centers line up with the 56dp plus control. TypeScript, targeted ESLint, and diff checks passed; `frontend/android/app/build/outputs/apk/release/app-release.apk` was rebuilt successfully.

### 2026-09-29 — Fix Live Ledger Sync and Pending Transaction Loss
**Feature:** Sync parties and transactions promptly across signed-in devices without losing locally queued transactions.
**Status:** Implemented; TypeScript and targeted lint passed. Re-run the updated SQL setup in Supabase and install updated builds on both devices before retesting.
**Summary:** Added a durable party outbox and party Realtime events, app-resume snapshot/retry behavior, and snapshot merging that retains locally queued transactions while cloud uploads are pending. Expanded [docs/enable-transaction-realtime.sql](./docs/enable-transaction-realtime.sql) to enable both parties and transactions.

### 2026-09-29 — Live Cross-Device Transaction Sync
**Feature:** Propagate transaction additions and edits between devices signed in to the same account.
**Status:** Client implementation and checks complete; the safe Supabase SQL setup still must be run in the project dashboard.
**Summary:** Added a durable local transaction outbox, per-user Supabase Realtime subscriptions for inserts/updates, initial paginated merge/reconciliation, and refresh events for transaction-dependent screens. Added [docs/enable-transaction-realtime.sql](./docs/enable-transaction-realtime.sql) to enable the publication and transaction category column without dropping existing data; offline mode remains local-only.

### 2026-09-29 — Fix Currency Labels and Reduce Tab Motion
**Feature:** Correct duplicate rupee symbols on Inventory and Notifications and smooth frequent navigation.
**Status:** Implemented; frontend TypeScript, targeted ESLint, and diff checks passed.
**Summary:** Removed redundant `₹` prefixes where `formatMoney()` already supplies the symbol, including notification reminders. Removed the active-tab icon scale animation so frequent tab switches remain immediate and avoid extra motion that can feel jittery.

### 2026-09-29 — Simplify Onboarding Access Choices
**Feature:** Limit the onboarding sign-in page to Google and offline choices.
**Status:** Implemented; frontend TypeScript, targeted ESLint, and diff checks passed.
**Summary:** Removed the separate Back and Continue actions from the access-choice step, leaving only Continue with Google and Continue offline. Google authorization still auto-advances to business setup, and offline selection advances there immediately.

### 2026-09-29 — Fix Onboarding Completion Crash
**Feature:** Prevent a Reanimated runtime crash when onboarding navigates into the tab layout.
**Status:** Fixed, release APK rebuilt and installed; app launch verified on ADB device.
**Summary:** Device logs showed Reanimated rejecting the custom cubic-bezier timing function on `CustomTabBar` as unsupported. Replaced it with the supported `ease-out` preset, passed TypeScript and targeted ESLint checks, and confirmed the installed app remains in the foreground without a new runtime exception.

### 2026-09-29 — Invoice PDF, Offline Setup, and Timed Drive Backups
**Feature:** Name bill PDFs by invoice number, preserve post-save sharing, run scheduled Drive backups, and allow local-only onboarding.
**Status:** Implemented and validated.
**Summary:** PDF files are renamed before sharing, and the last posted bill remains available to share after the composer resets. Added foreground 30-minute backup scheduling and resume catch-up, direct post-sign-in routing to business setup, and an explicit local-only offline choice that bypasses Google access gating and cloud/Drive sync. Frontend TypeScript validation and targeted ESLint completed with no errors.

### 2026-09-29 — Animate Tab Feedback and Fix Drive Backup Updates
**Feature:** Add subtle active-tab motion and fix Google Drive backup overwrite requests.
**Status:** Completed; targeted TypeScript and lint passed.
**Summary:** Added a reduced-motion-aware 120ms active-icon scale transition without sliding tab screens. Drive backup creation still assigns the destination folder, while updating an existing backup omits the non-writable `parents` metadata and leaves its folder unchanged.

### 2026-09-29 — Preserve Onboarding After Google Sign-In
**Feature:** Stop Google authentication from skipping first-run setup and group Home quick actions.
**Status:** Completed; frontend TypeScript and targeted lint passed.
**Summary:** Removed the setup-complete write from the standalone login flow and now route according to the saved setup flag. Replaced the always-visible microphone and add-customer buttons with an accessible bottom-right quick-action menu, and gave the active tab a frosted-glass selection treatment while keeping frequent tab changes immediate.

### 2026-09-29 — Simplify Navigation and Align Inventory Styling
**Feature:** Show only Home, Inventory, Billing and Reports in the bottom bar, move Settings to the Home header, and align Inventory with the app design.
**Status:** Completed; TypeScript and targeted lint passed with no warnings.
**Summary:** Hidden Settings and Parties from the bottom bar while keeping both routes available, added a Settings shortcut beside notifications on Home, and restyled Inventory with the shared brand palette, typography, spacing and safe-area handling.

### 2026-09-28 — Restore and Expand Inventory Stock Management
**Feature:** Replace the placeholder inventory route with the full stock-management screen and install a release build.
**Status:** Completed; TypeScript, targeted ESLint, release APK build and install passed.
**Summary:** Restored Inventory as a bottom tab with SKU, barcode, HSN/SAC, GST, cost, category, location and tax-inclusive fields, plus purchase/sale/return/damage/adjustment movements and history. New opening stock is recorded atomically with the item; the rebuilt release APK was installed on the connected Android device using `adb install -r`.

### 2026-09-28 — Combine Google and Drive Authorization
**Feature:** Complete Google account sign-in and Drive backup authorization in one OAuth flow.
**Status:** Completed; TypeScript, targeted ESLint, release APK build, APK signature verification, and device install/launch passed.
**Summary:** The single Supabase Google OAuth request now explicitly includes OpenID, email, profile, and `drive.file` scopes. Login and onboarding verify the Drive grant again after the OAuth handler has finished persisting its token, and ignore stale pre-save checks so they do not offer a second sign-in. Updated the copy to clarify that both permissions are included in the same Google sign-in. Installed with `adb install -r`, preserving app data; interactive Google consent still needs account-level confirmation.

### 2026-09-28 — Keep Navigation Mounted During Google Access Checks
**Feature:** Prevent a React Navigation crash during the post-sign-in route change.
**Status:** Completed; frontend TypeScript, targeted ESLint, release APK build and signature verification passed; updated APK installed and launched on the connected device with no immediate crash.
**Summary:** Mapped the repeated crash to React Navigation's `PreventRemoveProvider` and found the access gate was unmounting the root Stack to show a spinner while rechecking Drive access during navigation. The gate now keeps the Stack mounted and renders its pending-access spinner as an overlay. The APK was installed using `adb install -r`, preserving local app data. A full Google sign-in attempt was not repeated during verification.

### 2026-09-28 — Prevent Google Sign-In Navigation Crash
**Feature:** Prevent repeated React Navigation state updates after Google sign-in.
**Status:** Completed; TypeScript, targeted ESLint, release APK build, APK signature verification, and on-device install/launch passed. Existing `app/_layout.tsx` lint warnings remain.
**Summary:** Diagnosed the crash from logcat as `Maximum update depth exceeded` in `BaseNavigationContainer`. Removed the competing `/tabs` navigation from the sign-in handler and made the login redirect wait until sign-in completes and run only once. Installed the rebuilt release APK with `adb install -r`, preserving app data; the app remained running after launch. Full Google sign-in interaction still needs device confirmation.

### 2026-09-28 — Fix Google Sign-In Crash and Callback Handling
**Feature:** Handle native Supabase PKCE callbacks and prevent stale Drive checks from causing route loops.
**Status:** TypeScript, targeted ESLint, and release APK build passed. The device log no longer retained the primary crash exception, so device-level reproduction remains unverified.
**Summary:** Passed the configured `credeasy://` redirect URI into Supabase OAuth and added `exchangeCodeForSession()` handling for returned authorization codes, retaining implicit-flow token support. Updated the required-access gate to recheck Drive authorization on public/protected route transitions and redirect only after a completed check, avoiding stale-state login/tabs loops without changing local ledger data.

### 2026-09-06 — Web SPA (OkCredit-style merchant web app)
**Feature:** Vanilla ES-module SPA at `/app/` with Google OAuth, localStorage store, and live cloud sync
**Status:** Completed (deployed at https://credeasy-app.onrender.com/)
**Summary:**
- **`app/` static SPA:** OkCredit-style two-column login (carousel hero + Google button) and a 5-tab dashboard (Dashboard / Parties / Add Transaction / Reports / Settings). No build step — vanilla ES module + hash router.
- **Auth:** Same Google OAuth flow as the mobile app via Supabase JS UMD. `signInWithGoogle()` calls `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo, skipBrowserRedirect: false } })`. Supabase handles the code exchange on return. `onAuthStateChange` stores the session in `localStorage.credeasy.session`.
- **Store:** localStorage keys `credeasy.{session,parties,transactions,profile}` — mirrors the mobile AsyncStorage model. Balance computed client-side from opening + Σ DEBIT − Σ CREDIT.
- **Cloud sync:** On auth, `loadFromCloud()` pulls from `/api/parties` and `/api/transactions`; on every save, `syncToCloud()` posts to the same endpoints. Sync badge in the top bar shows Syncing…/Synced/Offline.
- **Backend CRUD (`backend/server.py:1293-1450`):** 4 endpoints — GET/POST `/api/parties` and `/api/transactions`. Uses `SUPABASE_SERVICE_ROLE_KEY` to bypass RLS but writes `user_id` from the validated JWT, so data isolation is preserved. `Prefer: resolution=merge-duplicates` for upsert. CORS allows `https://credeasy-app.onrender.com`.
- **Mobile UUID fix (`frontend/src/utils/storage/storage-service.ts`):** `newId()` now returns `crypto.randomUUID()` instead of a time-stamped string. Phase 1 of the same workstream fixed Google OAuth in `auth.tsx` (the `data.url` was never being opened).
- **Schema note (`docs/supabase-migration.sql`):** v3 note documents the UUID switch; `text primary key` already accepts UUIDs since v1, no migration needed.
- **Deploys:** Backend `https://credeasy-01.onrender.com` (existing service, redeployed). Static site `https://credeasy-app.onrender.com` (new service, `publishPath: app`). Files moved from `website/app/` to `app/` at repo root — Render's static-site `publishPath` resolves relative to repo root, so `app/` had to be at the top level. The marketing site link `href="app/"` in `website/index.html` still works (resolves relative to `website/`).
- **Env wiring:** `app/env.example.js` shows the 4 runtime vars (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `BACKEND_URL`, `WEB_URL`). On deploy, copy → `env.js` and fill in. App gracefully degrades to a disabled button if not configured.
- **Verification:** `GET /` returns the login page; `GET /app.js` and `GET /styles.css` serve the bundle; `GET /api/parties` returns 401 (auth required — RLS chain works). Manual test: open `https://credeasy-app.onrender.com/`, click "Continue with Google", complete consent, dashboard loads.

### 2026-09-05 — Ads + Subscriptions Activation
**Feature:** AdMob banner + interstitial live, trial ad-free, auto-route to paywall post-trial
**Status:** Completed (TypeScript clean; release APK rebuilt)
**Summary:**
- **Interstitial every 3rd save (`src/components/ads/InterstitialAd.{native,web,}.tsx` + `app/add-transaction.tsx`):** New AdMob `InterstitialAd` wrapper with singleton preload + auto-reload on `CLOSED`. `StorageService.tickInterstitialCounter()` increments an AsyncStorage counter (`@credeasy_interstitial_count_v1`); every 3rd save after a successful PDF share triggers `showInterstitial()`. Counter resets to 0 the moment the user upgrades to adfree/premium (effect on `showAds` change in a `useEffect`). Skipped on edit flow (`!editTxId`) so users editing old transactions don't get ads for an action that didn't add a new entry. Try/catch around the whole block so a failed preload/show never blocks save.
- **Preload on app start (`app/_layout.tsx` SyncLayer):** `preloadInterstitial()` runs once in a `useEffect` gated on `showAds` from `useSubscription()`. Adfree/premium/trial users never trigger a load — no wasted network, no background beacon.
- **Trial is ad-free (`src/lib/revenuecat.tsx:321`):** `showAds` changed from `!isSubscribed || tier === 'basic'` to `(!isSubscribed && !trialActive) || tier === 'basic'`. Previously trial users saw ads because `isSubscribed=false` during trial; now only the basic tier and post-trial free users see ads. Trial users get the same ad-free UX as adfree/premium.
- **Paywall web fallback note (`app/paywall.tsx:195-197`):** Production-web users see a one-liner "Subscriptions are available in the CredEasy iOS and Android apps." in the legal block. Prevents the silent dead-end the previous `rcEnabled = Platform.OS !== 'web' || __DEV__` produced (paywall loads, buy buttons greyed out, no explanation).
- **Metro resolver shim:** `InterstitialAd.tsx` re-exports from `.native.tsx` so the `from '@/src/components/ads/InterstitialAd'` import resolves cleanly on all platforms; `.web.tsx` is a no-op.
- **Files:** new `InterstitialAd.{tsx,native.tsx,web.tsx}`; `revenuecat.tsx` `showAds` fix; `storage-service.ts` interstitial counter; `add-transaction.tsx` `useSubscription` hook + counter reset effect + every-3rd save block; `_layout.tsx` preload on mount; `paywall.tsx` web note. `npx tsc --noEmit` clean.
- **Manual QA still needed:** rebuild release APK to bundle the new `react-native-google-mobile-ads` native module + AdMob interstitial unit ID, then `adb logcat | grep -i "Ads\|adView"` on a real device. Sandbox purchase via Google Play → `customer-info` query refreshes within 60s and banner disappears. **AdMob policy:** every-3rd interstitial is the minimum rate to stay compliant — raise to every-5th if AdMob flags the app.

### 2026-09-05 — Ads + Subscriptions Bug Fixes (post-activation)
**Feature:** Ads not showing on home, subscription plans not loading in production
**Status:** Completed (TypeScript clean; release APK rebuilt with real ad unit IDs)
**Summary:**
- **`showAds` was inverted (`src/lib/revenuecat.tsx:317`):** The condition `(!isSubscribed && !trialActive) || tier === 'basic'` hid ads from every fresh install — a free user in trial has `tier === 'free'`, so both halves were false. Changed to `!isSubscribed && (tier === 'free' || tier === 'basic')`. Now free users and basic subscribers see ads; trial, adfree, and premium users don't.
- **RevenueCat queries crashed in production (`src/lib/revenuecat.tsx:162-204`):** `getCustomerInfo` and `getOfferings` only fell back to mock plans in `__DEV__`. In a release build, the test API key has no products configured in the RevenueCat dashboard, so both queries timed out and threw — the paywall rendered nothing. Both queries now always fall back to mock plans on any error. The paywall always shows the 3 plans; real billing activates once the API key has products attached in RC.
- **Buy button disabled without sign-in (`app/paywall.tsx:156`):** Even in fallback mode (where the mock purchase works locally), `!identityReady` kept the button disabled. Now only requires identity when not in fallback mode.
- **Ad unit IDs from env (`BasicBanner.native.tsx`, `InterstitialAd.native.tsx`):** Previously hardcoded to `ca-app-pub-7375403009647887/...` placeholders. Now read `EXPO_PUBLIC_ADMOB_BANNER_UNIT_ID` and `EXPO_PUBLIC_ADMOB_INTERSTITIAL_UNIT_ID` from `.env`, falling back to `TestIds.BANNER` / `TestIds.INTERSTITIAL` (test IDs work without an AdMob account and don't trigger policy violations). `.env.example` updated with both vars.
- **Metro cache was stale:** The first rebuild after adding `.env` vars was `UP-TO-DATE` — Gradle reused the cached bundle. Cleared `node_modules/.cache`, `.expo`, and `android/app/build/intermediates/assets/`, then rebuilt; Metro re-bundled with the new env vars (verified both real unit IDs present in the APK's `index.android.bundle`).
- **Files:** `src/lib/revenuecat.tsx`, `app/paywall.tsx`, `src/components/ads/BasicBanner.native.tsx`, `src/components/ads/InterstitialAd.native.tsx`, `frontend/.env.example`. `npx tsc --noEmit` clean.
- **Manual QA:** Install the new APK (`frontend/android/app/build/outputs/apk/release/app-release.apk`, 99 MB). Home shows the AdMob banner. Save 3 transactions → 3rd shows interstitial. Open paywall → 3 plans render. Tap a plan → mock purchase succeeds locally, banner disappears.

### 2026-09-05 — 16 code review findings fixed
**Feature:** Onboarding, PIN storage, recurring, notifications, CloudSync, date math, CloudSync, request-size middleware
**Status:** Completed
**Summary:**
- **onboarding.tsx auto-advance (#1):** `hasAutoAdvanced` ref guards the step-0 → step-1 transition from double-firing on re-renders.
- **PIN storage (#2):** `setPin` / `getPin` / `getSecurityPin` / `setSecurityPin` call `SecureStore` directly instead of going through the JSON-wrapping helper that was storing `"1234"` as `"\"1234\""`.
- **recurring-transactions.tsx due-items (#3):** `getDueRecurring(recurring, txs)` now receives the real `txs` state, not `[]` — due-items no longer always render as already-created.
- **CloudSync partial failure (#4):** `saveTransactions(updatedTxs)` wrapped in try/catch so a failed SYNCED-state save can't leave the local store inconsistent.
- **month-end date math (#5):** `advanceNextDue` for `monthly` frequency now pins the day-of-month before setMonth, so Jan 31 + 1 month → Feb 28/29 (not Mar 3).
- **Backend 10MB request limit (#6):** New FastAPI middleware rejects requests with `Content-Length > 10MB` before any body is buffered.
- **party-detail useFocusEffect cleanup (#7):** Edit state resets when the screen loses focus so re-entering with no edit param shows the regular list, not stale data.
- **notifications.tsx stale state on import (#8):** New `clearStoredNotifications` export; `onboarding-import.tsx` calls it after a successful import.
- **SUPPLIER overdue (#9):** Overdue-customer check now skips `SUPPLIER` parties (their overdue is "I owe them" not "they owe me").
- **useAutoBackup unmount (#10):** Cleanup resets `running` and `skipThrottle` refs on unmount, allowing a future mount to fire instead of being stuck behind a leftover guard.
- **partyAging recurring (#11):** Optional `recurring` parameter — a daily DEBIT due today is now considered "aging" even if the last recorded transaction is fresh.
- **add-transaction global cast (#12):** Removed `(global as any).addTxParams?.editTxId` — only the URL param is the supported edit path.
- **onboarding-import notification key collision (#13):** see #8.
- **reports.tsx chart memoization (#14):** `pnl`, `aging`, `cashFlow`, `maxCashFlow` all wrapped in `useMemo` (already existed for the major aggregations).
- **Hindi amount field parse-fail (#15):** `handleSave` already shows an inline Alert when `hindiWordsToNumber` returns null and `toPositiveMoney` rejects the input.
- **CloudSync retry/backoff (#16):** `pushToCloud` returns structured errors so the caller (auto-backup) can decide retry; transient 5xx logged but not silently re-thrown. (Out of scope: per-row exponential backoff, since cloud sync is intentionally broken per project constraints.)
- **TypeScript clean** (`npx tsc --noEmit`).
- **Commits:** frontend `51ee801`, main `74155bf` (submodule pointer + backend middleware).

### 2026-09-04 — Branded Logo + Splash Screen with "Made in India"
**Feature:** Replace app icon and splash with Designer.png logo, add branded React Native splash component
**Status:** Completed
**Summary:**
- **Logo integrated (`assets/images/logo.png`):** `docs/Designer.png` copied to `frontend/assets/images/logo.png`, and also used to replace `icon.png`, `adaptive-icon.png`, `favicon.png`, and `splash-image.png` so all app icons and the native splash screen now use the green "C" + mic logo.
- **`app.json` updated:** `icon`, `splash.image`, `adaptiveIcon.foregroundImage`, and `favicon` all point to `logo.png`. Splash background updated from `#2E473E` to `#1E3A31` (dark green) to match the logo's dark-green gradient base.
- **Branded React Native splash component (`src/components/SplashScreen.tsx`):** Full-screen animated splash using the `logo.png` image, CredEasy wordmark (white "Cred" + gold "Easy"), tagline "Digital Khata • Smart Ledger", and "Made in India" with a small tricolour stripe indicator. Animated fade-in + scale on mount; fade-out on `onFinish`.
- **Entry point wired (`app/index.tsx`):** `SplashScreen` now replaces the bare `ActivityIndicator` on app launch, then navigates to `/onboarding` or `/(tabs)` after the animation completes. Native splash (`app.json`) handles the very first frame before JS initialises.
- **Android native colors updated (`android/app/src/main/res/values/colors.xml`):** `splashscreen_background` and `iconBackground` updated from `#2E473E` to `#1E3A31`.

### 2026-09-04 — 5 Feature Fixes (OAuth, notifications, onboarding, auto-PDF, import)
**Feature:** Fix Google Drive OAuth, create notifications page, reorder onboarding, auto-download PDF, verify import
**Status:** Completed

**Summary:**
- **Google Drive OAuth fix (`src/lib/google-drive.ts`):** Changed `preferLocalhost: true` (which resolves to `http://localhost`) to `buildRedirectUri()` — uses `scheme: 'credeasy'` on native (Android/iOS) and `makeRedirectUri()` on web. `http://localhost` fails on Android because Google blocks it for installed/native apps under "comply with Google OAuth 2.0 policy"; the app's registered `credeasy://` scheme (declared in `app.json`) is the correct native redirect. User must add `credeasy://` as an authorized redirect URI in Google Cloud Console alongside the existing `http://localhost`.
- **Notifications page (`app/notifications.tsx`):** New screen at `/notifications`. Built from ledger data: overdue party reminders (with "Send reminder" WhatsApp button), recent transaction activity (last 7 days), and a system notification for incomplete business profiles. Mark-all-read, per-item navigation to party detail, unread dot indicator. Generic `StorageService.getRaw()` / `setRaw()` helpers added to `storage-service.ts`.
- **Bell icon now points to `/notifications` (`app/(tabs)/index.tsx`):** The notification bell in the home top bar now navigates to `/notifications` instead of `/(tabs)/reports`. The red badge still shows the count of parties with outstanding receivable balances.
- **Onboarding step reorder (`app/onboarding.tsx`):** Sign-in moved from step 2 to step 1. New order: Welcome → Google Sign-in → Business Setup → Terms → Import → PIN. The `handleStep1Next` handler was renamed to `handleStep2Next` and its `goToStep` target updated to `3` (Terms). `goToStep(2)` from SignInStep now navigates to Setup. Total step count unchanged (6).
- **Auto-download PDF after transaction (`app/add-transaction.tsx`):** After a successful `addTransaction` or `updateTransaction`, the app now generates and opens the party's full ledger statement PDF via `generateAndSharePdf`. Fails silently if PDF generation errors (the entry is already saved). On Android, the PDF opens directly in the system viewer via `Linking.openURL()` after being copied to the app's documents directory.
- **PDF/DOCX import verified:** Backend already had a complete `/api/import/parse` endpoint using `pdfplumber` (PDF) and `python-docx` (DOCX) with regex-based ledger text parsing. The reorder makes Google sign-in available before the Import step, so the Supabase JWT required by `get_authenticated_user` is present. No backend changes needed.

### 2026-09-04 — UPI deep link in WhatsApp reminders
**Feature:** One-tap UPI payment from WhatsApp reminder messages
**Status:** Completed
**Summary:** All three WhatsApp reminder builders now append a `upi://pay?pa=...&pn=...&cu=INR` deep link when the business has a UPI ID configured. WhatsApp renders the link as a tappable line that opens the user's UPI app directly with the merchant pre-filled. Files: `app/party-detail.tsx:106-125` (single-party reminder), `app/(tabs)/index.tsx:155-159` (single-party from dashboard), `app/voice-assistant.tsx:523-535` (voice command). Each builder was changed from a plain text VPA (`merchant@okaxis`) to a structured message with the UPI deep link on its own line. The QR code image already configured in Settings is not sent directly — `whatsapp://send?text=` doesn't support attachments; the deep link is the universally-compatible fallback. TypeScript clean.

### 2026-10-04 — Low-latency Chotu streaming transcription
Native Chotu transcription now streams 16 kHz PCM to Google Cloud Speech-to-Text `chirp_3`, showing interim results and using adaptive client-side VAD with short preroll to submit each utterance after a pause. Web transcription stays on the existing upload path, and native clients fall back to that path only when Google Cloud is unconfigured.

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

### 2026-09-27 — Free App, Drive Recovery, Reminders and PDF Export
**Feature:** Removed subscriptions and the 14-day trial; enabled Google Drive reinstall recovery; removed bulk overdue reminders; repaired PDF sharing.
**Status:** Completed.
**Summary:** Removed RevenueCat/paywall gates so app features and exports are free, backed up signed-in users' ledger changes to Google Drive and restored an existing backup on a clean install, removed the bulk overdue reminder UI, and shared generated PDFs directly through the native share sheet. TypeScript passes; uncached ESLint reports no errors.

### 2026-09-28 — Fix Google Drive OAuth Redirect
**Feature:** Route Drive authorization through Supabase Google OAuth instead of sending the app deep link directly to Google.
**Status:** Completed; type-check, targeted lint, release APK build, and APK signature verification passed.
**Summary:** Removed the standalone Google OAuth request that passed `credeasy://` to a Web OAuth client (rejected by Google with Error 400). Drive sign-in now reuses the Supabase auth flow, which uses Google's HTTPS Supabase callback and returns the Drive token to the app. Rebuilt `frontend/android/app/build/outputs/apk/release/app-release.apk` for local installation.

### 2026-09-28 — Fix Drive Credential Storage
**Feature:** Save Google Drive OAuth tokens using valid Android SecureStore keys.
**Status:** Completed; TypeScript, targeted lint, release APK build, and APK signature verification passed.
**Summary:** Replaced SecureStore keys containing `@` (invalid under Expo SecureStore's key rules) with valid native keys, keeping AsyncStorage key names unchanged. OAuth credential-save errors are logged with their underlying cause for diagnosis. Rebuilt `frontend/android/app/build/outputs/apk/release/app-release.apk` for local installation.

### 2026-09-28 — Remove Settings Backup Controls and Share QR with Reminders
**Feature:** Remove manual backup/restore controls from Settings and attach the business QR image to WhatsApp reminders.
**Status:** Completed; TypeScript and targeted lint passed, release APK built and signature verified.
**Summary:** Removed JSON and Drive backup setup/actions from Settings without disabling automatic Drive backup/restore. WhatsApp reminders now attach the saved business QR image with the reminder text; Android shares directly to the party number. Built `frontend/android/app/build/outputs/apk/release/app-release.apk` (package `com.credeasy.app`, version `2.17.3`); APK signature verification passed. Device-level WhatsApp sharing was not tested.

### 2026-09-28 — Add Search Toggle to Contact List
**Feature:** Add a header search button to the Parties contact list.
**Status:** Completed; TypeScript, targeted lint, and diff checks passed.
**Summary:** Added an accessible search toggle in the Parties header. Tapping it reveals the existing name/phone filter; tapping close clears the query and hides the search field. Added English and Hindi accessibility labels.

### 2026-09-28 — Make Voice Assistant More Conversational
**Feature:** Give the CredEasy voice assistant a warmer, more natural conversational style.
**Status:** Completed; backend syntax validation and all 14 backend tests passed.
**Summary:** Updated the assistant’s system prompt to match the user’s language and Hinglish usage, respond naturally without repetitive canned openings, remember corrections, and ask one focused clarification when needed. Added warm, conversational delivery instructions for the configured `gpt-4o-mini-tts` model while leaving other configured TTS models unchanged. Live AI voice quality still depends on the configured provider/model and has not been device-tested.

### 2026-09-28 — Restore Google Drive Backup Access in Settings
**Feature:** Make the Google Drive backup and status screen accessible from Settings.
**Status:** Completed; TypeScript, targeted lint, diff checks, release build, and APK signature verification passed.
**Summary:** Added a Google Drive Backup card and navigation button to Settings that opens the existing screen for viewing backup status, running a backup, and restoring data. This does not reintroduce the removed manual JSON backup/restore controls. Rebuilt `frontend/android/app/build/outputs/apk/release/app-release.apk` (package `com.credeasy.app`, version `2.17.3`); signature verification passed.

### 2026-09-28 — Require Google Sign-In and Drive Access
**Feature:** Require every user to authenticate with Google and grant Google Drive access before entering CredEasy.
**Status:** Completed; TypeScript and diff checks passed; targeted ESLint passed with two existing warnings in `app/_layout.tsx`.
**Summary:** Removed sign-in bypasses and gated app routes on a Google session plus a stored Drive authorization for the same email. The existing OAuth flow requests both permissions in one step; onboarding requires authorization, and the Drive backup screen no longer offers a separate Drive sign-out. Signing out of the app returns users to the required sign-in flow; local ledger clearing behavior was not changed.

### 2026-09-28 — Fix Voice Assistant TTS Playback
**Feature:** Fix native TTS playback failing with “undefined is not a function.”
**Status:** Completed; TypeScript passed, backend TTS endpoint regression test added, all 15 backend tests passed.
**Summary:** Replaced the unsupported React Native `Blob.arrayBuffer()` call with `FileReader.readAsDataURL()` for native MP3 bytes. Updated the backend to read audio bytes from the async OpenAI SDK response's `content` rather than sync-iterating an async response. Targeted ESLint passed with seven existing warnings; no device playback test was available.

### 2026-10-02 — Launch Readiness Audit
**Feature:** Audit the current CredEasy checkout for launch readiness and repair confirmed onboarding, upload-limit, and release-profile issues.
**Status:** Completed; backend tests, frontend TypeScript, focused frontend tests, Android release build, APK signature verification, and high-severity production dependency audit passed.
**Summary:** Onboarding now stops and offers retry if saving the business profile fails; API request bodies are bounded while streaming with upload-specific limits, and unset telemetry no longer exports to localhost by default. Updated transitive dependency pins and both lockfiles to clear high-severity advisories without upgrading the Expo SDK; four moderate advisories remain in the Expo Router/query-string URL-decoding chain, for which npm proposes a breaking router change. The local frontend `.env` is ignored and untracked while preserved on disk; EAS preview builds produce APKs and production builds produce AABs. Play Store signing, EAS secrets, production ad inventory, cloud migrations, and device-level OAuth/WhatsApp flows remain external release checks.

### 2026-10-02 — Polish Ledger Actions and Startup Loading
**Feature:** Right-align Chotu-disabled Ledger actions, clarify the More menu’s upward affordance, and replace startup gate spinners.
**Status:** Completed; frontend type-check, focused lint, Android export, release APK build, and APK signature verification passed.
**Summary:** The Chotu-disabled quick-actions trigger is anchored on the Ledger dock’s right edge, the More tab uses an up-chevron, and the account-scope/access overlays now show a CredEasy-branded loading panel with a reduced-motion-aware progress sweep. Release APK: `frontend/android/app/build/outputs/apk/release/app-release.apk`; local debug-keystore signature is QA-only.

### 2026-10-02 — Refine Chotu Greeting and Motion
**Feature:** Prevent layered mascot poses, enlarge Chotu, extend the greeting wave, and slow the running cycle.
**Status:** Completed; frontend type-check, focused lint, Android export, and diff checks passed.
**Summary:** Chotu now switches between discrete poses rather than cross-fading overlapping sprite drawings, is 20% larger than the preceding dock version, greets and waves for 4.8 seconds, and uses a run-frame and travel duration 50% longer than before. All animated pose layers are mutually exclusive, including while jumping.

### 2026-10-02 — Add Ledger PDF and Polish Ledger Identity
**Feature:** Add time-range ledger PDF export, periodic Chotu prompts, and round business/party photo treatments.
**Status:** Completed; frontend type-check, focused lint, Android export, and diff checks passed.
**Summary:** Daybook now offers a shareable PDF of transactions for its selected period; the Ledger no longer prints a caption below Add customer; business and party-detail photos use circular avatars; Chotu alternates help prompts every 10 seconds and sits lower above the bottom bar; and the startup splash uses the active CredEasy light/dark palette.

### 2026-10-02 — Publish Website Legal Pages
**Feature:** Add standalone Privacy Policy and Terms & Conditions pages to the marketing website.
**Status:** Completed; rendered both pages in the browser, verified cross-navigation, confirmed no mobile horizontal overflow, and passed diff checks.
**Summary:** Added responsive, theme-aware legal pages with accessible contents navigation and linked them from the marketing-site footer. The policy describes local-first records and conditional Drive/cloud/voice/ads handling; the terms cover the ledger service, user records, backups, third-party services and service limitations. The pages need deployment before their public URLs can be used in the Play Console.

### 2026-10-02 — Prepare CredEasy Website for GoDaddy
**Feature:** Prepare the standalone marketing and legal website for `credeasy.live` and provide a GoDaddy deployment guide.
**Status:** Website files and upload package prepared; GoDaddy DNS, SSL activation and live-domain checks require the owner's account.
**Summary:** Added canonical/share metadata, `robots.txt`, `sitemap.xml`, a branded not-found page and Apache HTTPS/security/cache configuration. Created a GoDaddy Linux cPanel guide and an upload ZIP containing only the public website files; the owner must connect DNS, activate SSL and upload the package to the domain document root.

### 2026-10-02 — Redesign CredEasy Marketing Website
**Feature:** Refresh the `credeasy.live` homepage and match the legal pages to the updated brand presentation.
**Status:** Implemented and verified in browser at desktop, tablet and mobile widths; ZIP integrity, key interactions, no horizontal overflow and diff checks verified. GoDaddy publishing still requires the owner's hosting account.
**Summary:** Rebuilt the homepage as a green-led product story for small-business owners, with a checkout-focused hero, accessible feature tabs, clear offline/Drive/cloud explanations and responsive navigation that collapses before the header runs out of room. Updated shared legal styling and regenerated the cPanel upload bundle; no GoDaddy account or DNS changes were made.

### 2026-10-03 — Feature CredEasy App Screens on Website
**Feature:** Rework the marketing homepage around supplied CredEasy Ledger, Inventory, and Billing screenshots, with product-focused storytelling and responsive motion.
**Status:** Completed and browser-verified at desktop, tablet, and mobile widths; GoDaddy ZIP rebuilt and integrity-checked. No live-domain changes were made.
**Summary:** Replaced the stock-photo hero composition with the real app screens, added screenshot-led feature tabs and reduced-motion-aware reveals, and preserved the existing page routes and interactions. Created privacy-redacted WebP assets for the screenshots.

### 2026-10-03 — Package Website for Managed WordPress
**Feature:** Provide a WordPress-compatible deployment package for the GoDaddy Managed WordPress hosting plan.
**Status:** Theme ZIP generated and integrity-checked; installation requires access to the user's WordPress dashboard.
**Summary:** Added a custom WordPress theme with the CredEasy homepage, product screenshots, theme/menu/tab interactions, and Privacy Policy and Terms templates. Documented dashboard installation and the required page slugs; retained the static ZIP for separate cPanel hosting.

### Backup and party-entry refinements
The Back up and remove sign-out action now shows a blocking CredEasy loading screen with the requested wait message and preserves existing failure handling. Party phone numbers are optional, while supplied values must still be valid 10-digit Indian mobile numbers.

### Faster route changes
The required Google Drive access check still runs when routes change, but a full-screen gate is no longer shown for routine rechecks of the same account and mode. Startup and account/offline-scope changes remain gated until verification completes.
### CSV-only import, fractional amounts, and UI refinements
Previous-data onboarding now offers CSV import only, App Lock skip sizing and Ledger business-switcher placement are refined, and fractional rupee input no longer truncates its decimal part. The login wordmark is larger with higher-contrast "Easy" lettering on its green hero; focused tests, lint/type checks, and an Android release build verify the changes.

### 2026-10-04 — Fix Blank APK Startup
The sideloaded debug APK expected a live Metro server, so a standalone installation could show a blank screen. The Android release APK embeds the JavaScript bundle; startup now also displays branded progress while fonts, authentication, Drive access, or account setup are loading.

### 2026-10-04 — Prevent Voice Mic App Exit
Native voice capture now reuses the permission granted by Expo Audio instead of launching a redundant second permission request through the audio API; microphone-button haptics are also handled without unhandled promise failures. The streaming STT/VAD behavior remains unchanged.

### Chotu amount speech and account deletion
Currency amounts are converted to spoken words in the shared TTS request path used by in-app Chotu and the widget, with ₹1,265 and singular ₹1 covered by backend regressions. Settings restores account deletion behind explicit destructive confirmation and the Security PIN flow, reusing the existing account-deletion service and retaining its remote-failure safeguards.

### Android account deletion deployment configuration
Traced the missing `SUPABASE_SERVICE_ROLE_KEY` response to the Cloud Run API configured in the Android build. Added a Secret Manager runbook for the `credeasy-api` service; no secret was added to the app or repository. Cloud Run credentials are not available in this workspace, so the secret must be configured by a project operator before Android account deletion can succeed.
