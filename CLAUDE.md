# CredEasy - Project Context

## Project Overview
A mobile-first business ledger app (React Native + Expo) with Supabase backend, voice assistant, subscriptions (RevenueCat), and ads (AdMob). Offline-first architecture where cloud sync has known issues.

## Tech Stack
- **Frontend:** React Native / Expo (TypeScript, Strict TypeScript)
- **Backend:** Python/Flask (`backend/`)
- **Database:** Supabase (Postgres, Auth, RLS, Storage)
- **Auth:** Supabase OAuth (Google)
- **Subscriptions:** RevenueCat
- **Ads:** AdMob via `react-native-google-mobile-ads`
- **Storage:** AsyncStorage (primary), Supabase (cloud backup)

## Key Constraints (Do Not Break)

### Cloud Sync Architecture
- **Cloud sync is deliberately broken** - do not "fix" sign-out data clearing until sync actually works
- The app generates string IDs (e.g., `party-1740...`) while Supabase expects UUIDs
- AsyncStorage is the **only** copy of the ledger until UUID schema is fixed
- See `docs/FIXING-GUIDE.md` for the repair order if/when sync is prioritized

### Auth/Session Issues
- Client stores Supabase JWT; backend uses `st_...` tokens in `db.user_sessions` — different systems
- `saveToken()` in auth lib is defined but never called
- `/api/auth/session` endpoint is dead code
- `signInWithOAuth` returns consent URL in `data.url` that code never opens
- Client rebuilt per call with `persistSession: false` — no persistent Supabase session

### Database Schema
- App generates string IDs like `party-1740…-a1b2c3d4`
- Supabase expects UUID primary keys
- All cloud upserts fail; cloud sync has **never worked**
- `docs/supabase-migration.sql` declares UUID primary keys (migration needed)

### RLS Policies
- UPDATE policies have `USING` but no `WITH CHECK` (users can reassign row `user_id`)
- `business_profiles` has no DELETE policy
- RLS IS enabled with `auth.uid() = user_id` policies (correct)
- `EXPO_PUBLIC_SUPABASE_ANON_KEY` is designed to be public — RLS is the access control
- `service_role` key must never ship

### Other Known Issues
- `react-native-google-mobile-ads` is not installed — Basic tier ads are documented no-op
- `rcEnabled = Platform.OS !== 'web' || __DEV__` makes production-web paywall impassable
- Backend 401s on all authenticated calls (voice assistant included)

### Android Build Fix (Resolved 2026-09-04, updated 2026-09-04 v2)
Local `./gradlew assembleDebug` / `assembleRelease` now works on Windows + NDK 27. The fix lives in two places:
1. **`patchCxxSharedLib` Gradle task** (`android/app/build.gradle`, runs before every native build via `preBuild.dependsOn patchCxxSharedLib`): walks every `CMakeLists.txt` under `react-native-screens`, `react-native-worklets`, `react-native-reanimated`, `react-native-gesture-handler`, `react-native-safe-area-context`, `react-native-webview`, `react-native-purchases-ui`, `react-native-google-mobile-ads`, `expo-modules-core`, and `@react-native-async-storage/async-storage`. For each file: (a) inserts `find_library(CPP_SHARED_LIB c++_shared)` before the first `add_library(...)` if missing; (b) walks every `target_link_libraries(...)` call (handles both single-line `target_link_libraries(foo bar)` and multi-line `target_link_libraries(\n  foo\n)` forms via balanced-paren matching) and appends `${CPP_SHARED_LIB}` to any block that doesn't already have it. The patch is idempotent — re-running on an already-patched file is a no-op. Survives `gradle clean`, `npx expo prebuild`, and `yarn install`.
2. **Standalone Node.js patcher** (`frontend/scripts/patch-all-cmake.js`): same logic in plain JS for one-off pre-patching without running gradle. Useful if you need to inspect or fix files before a long build, or to understand which blocks were patched.
**Known cosmetic warning:** `CMAKE_OBJECT_PATH_MAX=250` warning on Windows for paths with spaces — non-fatal, build proceeds. APKs at `frontend/android/app/build/outputs/apk/debug/` and `.../release/`.

## File Locations

### Frontend
```
frontend/src/
├── lib/
│   ├── auth.tsx          # Supabase auth, signIn/signOut
│   ├── revenuecat.tsx    # RevenueCat integration
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
