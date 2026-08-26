# CredEasy — Fixing the 6 Open Items

A step-by-step guide written for someone who has not shipped an app before.
Work through it **in order**. Each part says what is broken, why, exactly what to
type, and how to prove it worked before you move on.

Budget roughly: Part 0 (20 min) · Part 1 (2–3 h) · Part 2 (30 min) · Part 3
(30 min) · Part 4 (2 h) · Part 5 (30 min) · Part 6 (2–4 h, mostly waiting on
builds) · Part 7 (a decision, then 10 min).

---

## Two corrections before you start

I got two things slightly wrong in my audit report. Fix your mental model now so
you don't waste time on non-problems:

**1. `EXPO_PUBLIC_SUPABASE_ANON_KEY` is *supposed* to be public.**
It ships inside your app bundle and anyone can extract it. That is by design —
it is not a password. The "anon key" only says *"I am some client of this
project."* What actually stops user A reading user B's ledger is **Row Level
Security (RLS)**: rules inside Postgres that check the signed-in user's identity
on every single query. So do **not** spend any time trying to hide the anon key.
Spend it on Part 3 instead.

(The key you must *never* ship is the **service_role** key. Check that it appears
nowhere in `frontend/`. It belongs on a server only.)

**2. `docs/supabase-migration.sql` already has correct RLS policies.**
My report said RLS was "disabled". The *SQL file* enables it properly. The claim
came from a stale code comment in `frontend/src/lib/supabase.ts:8-10`. What you
actually need to do is (a) confirm RLS is really ON in your live project, (b) fix
two genuine gaps in those policies, and (c) delete the misleading comment.

---

## The single root cause

The 6 items look like 6 separate bugs. They are mostly **one** bug with a long
shadow. Here is the chain:

```
frontend/src/lib/auth.tsx  calls  supabase.auth.signInWithOAuth()
        │
        │  That call does NOT sign anyone in. It only *builds a URL*
        │  and hands it back to you in `data.url`.
        │  Your code throws `data.url` away and never opens it.
        ▼
No browser ever opens  →  Google never asks the user to approve
        ▼
No Supabase session exists  →  no JWT (the signed "this is user X" token)
        ▼
        ├──► auth.uid() is NULL inside Postgres
        │       → every RLS policy says "no"  → sync returns 0 rows
        │
        ├──► user_id UUID REFERENCES auth.users(id) can never be satisfied
        │       → every INSERT is rejected  → sync has never written anything
        │
        └──► the app has no token to send to your FastAPI backend
                → the voice assistant 401s
```

So: **Part 1 is the keystone.** Nothing downstream can be tested until sign-in
actually completes. Resist the urge to jump to Part 6 (ads) because it looks
easier — it is the only part that is genuinely independent, and it's last for a
reason (it needs a slow native build).

---

## Part 0 — Safety net (do this first, it is 20 minutes)

### 0.1 Put the project under version control

Your project is **not** a git repository. That means right now you have no undo.
The first time an edit goes wrong you will lose work. Fix that:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main" && git init && git add -A && git commit -m "Working state before auth and sync rework"
```

If that complains about `git` not being found, install Git for Windows from
<https://git-scm.com/download/win>, then reopen your terminal.

From now on, **commit after every part of this guide that you verify**:

```bash
git add -A && git commit -m "Part 1: Google sign-in completes"
```

If a part goes badly, you can throw away the mess with:

```bash
git checkout -- . && git status
```

Also confirm your secrets are not being committed:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main" && git check-ignore -v frontend/.env backend/.env
```

If that prints nothing, the `.env` files are **not** ignored. Create a
`.gitignore` at the project root containing at least:

```
node_modules/
.env
*.env
.expo/
dist/
__pycache__/
*.pyc
```

then run `git rm -r --cached . && git add -A && git commit -m "Apply gitignore"`.

### 0.2 Back up the only real copy of the data

Sync has never worked, which means **AsyncStorage on the phone is the only copy
of any real ledger data**. If you have been testing with data you care about,
export it before touching anything: open the app → Settings → whatever
export/backup option exists, and save the file off the device. If there is no
data you care about, skip this — but know that this is *why* Part 5 (sign-out
clearing data) is dangerous and comes late.

### 0.3 Know your two dashboards

You will be switching between these constantly. Open both in tabs now:

| What | Where | Used in |
|---|---|---|
| Supabase project | <https://supabase.com/dashboard> | Parts 1, 2, 3 |
| Google Cloud console | <https://console.cloud.google.com/apis/credentials> | Part 1 |
| AdMob | <https://apps.admob.com> | Part 6 |

Find your **project ref** now — it's the random-looking string in your Supabase
URL, e.g. `https://abcdefghijklm.supabase.co` → ref is `abcdefghijklm`. Write it
down; several steps need it.

### 0.4 The one Expo gotcha that will waste your afternoon

Anything named `EXPO_PUBLIC_*` in `frontend/.env` is **baked into the JavaScript
bundle when the bundler starts**. Editing `.env` while the dev server is running
changes *nothing*. Every single time you edit `frontend/.env`:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx expo start -c
```

The `-c` clears the cache. Without it you will be debugging a stale value and
concluding the code is broken.

---

## Part 1 — Make Google sign-in actually complete

**Item fixed:** the root cause of items #2, #3 and #4.

### 1.1 What is actually wrong

Three separate mistakes stack up in `frontend/src/lib/auth.tsx`:

1. **`getSupabaseClient()` builds a brand-new client on every call** (line 56).
   The Supabase client holds the session in memory. A new client has no session,
   so even a successful sign-in would be forgotten the moment the function
   returned.
2. **`persistSession: false, autoRefreshToken: false`** (lines 62-63) tell the
   SDK: *do not save the session to disk, and do not renew it when it expires.*
   Both must be `true`.
3. **`signInWithOAuth`'s return value is discarded** (lines 125-136). It returns
   `{ data: { url } }` — a Google consent URL. Somebody has to open that URL in a
   browser, wait for the user to approve, catch the redirect back into the app,
   and pull the tokens out of it. None of that happens.

Also worth knowing: `saveToken()` at line 32 is defined but never called
anywhere. Once Supabase manages the session properly, `saveToken` / `getToken` /
`clearToken` become dead code and we delete all three. (Bonus: they used
`SecureStore`, which has a **~2048-byte limit per value** on iOS. A Supabase
access token + refresh token pair can exceed that and fail silently. AsyncStorage
has no such limit.)

### 1.2 Configure Google in the Google Cloud console

You need an OAuth client so Google will trust your Supabase project.

1. Go to <https://console.cloud.google.com/> and create a project (or pick one).
2. **APIs & Services → OAuth consent screen.** Choose **External**. Fill in app
   name (`CredEasy`), your support email, developer email. Save. You do *not*
   need to submit for verification while testing — but you **must** add your own
   Google account under **Audience → Test users**, or sign-in will be rejected
   with `access_denied`.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID.**
   - Application type: **Web application** (yes, "Web" — even for a phone app.
     The browser round-trip happens on Supabase's servers, so Google sees a web
     client. This trips up nearly everyone.)
   - Name: `CredEasy Supabase`
   - **Authorized redirect URIs** → Add URI, exactly this, with your ref:
     ```
     https://YOUR-PROJECT-REF.supabase.co/auth/v1/callback
     ```
   - Create. Copy the **Client ID** and **Client secret**.

### 1.3 Configure Google in Supabase

1. Supabase dashboard → **Authentication → Sign In / Providers → Google**.
2. Toggle **Enable Sign in with Google** on.
3. Paste the Client ID and Client secret from 1.2. Save.

4. Now → **Authentication → URL Configuration**. This is the allow-list of places
   Supabase is willing to send a user back to after login. If a URL isn't here,
   Supabase silently redirects to your Site URL instead and your app never sees
   the tokens.

   - **Site URL**: `http://localhost:8081` (change to your real web domain later)
   - **Redirect URLs** — add each of these on its own line:
     ```
     credeasy://
     credeasy://*
     exp://**
     http://localhost:8081/**
     ```
   `credeasy` is your app's custom URL scheme — it's already declared as
   `"scheme": "credeasy"` in `frontend/app.json`, so you don't need to add it.
   The `exp://**` line is what makes sign-in work while testing in Expo Go.

### 1.4 Create one shared Supabase client

Right now **two** files build their own client: `auth.tsx` and `supabase.ts`.
They cannot see each other's session, which is a second reason sync would fail
even after login worked. We make one client and share it.

Create a new file `frontend/src/lib/supabase-client.ts`:

```ts
/**
 * The single Supabase client for the whole app.
 *
 * There must be exactly one. The client object *is* where the signed-in
 * session lives, so a second client is a second, empty session — which is why
 * auth.tsx and supabase.ts each building their own meant nothing was ever
 * actually signed in from the database's point of view.
 */
import { AppState, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

/** True when the project is configured at all. Callers use this to degrade
 *  gracefully instead of crashing on a missing .env value. */
export const supabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!supabaseConfigured) {
    throw new Error(
      'Supabase is not configured. Set EXPO_PUBLIC_SUPABASE_URL and ' +
      'EXPO_PUBLIC_SUPABASE_ANON_KEY in frontend/.env, then restart with `npx expo start -c`.'
    );
  }
  if (client) return client;

  client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: {
      // AsyncStorage, not SecureStore: SecureStore caps each value at ~2048
      // bytes on iOS and a JWT pair can exceed that, failing quietly.
      storage: AsyncStorage,
      persistSession: true,
      autoRefreshToken: true,
      // On web the tokens come back in the page URL and the SDK can pick them
      // up itself. On native the browser hands the URL to us, so we call
      // setSession() by hand and must not let the SDK also try.
      detectSessionInUrl: Platform.OS === 'web',
    },
  });

  if (Platform.OS !== 'web') {
    // Access tokens expire after an hour. React Native throttles timers in the
    // background, so without this the refresh timer can miss its slot and the
    // user is silently logged out on next launch.
    AppState.addEventListener('change', state => {
      if (state === 'active') client?.auth.startAutoRefresh();
      else client?.auth.stopAutoRefresh();
    });
  }

  return client;
}
```

### 1.5 Rewrite `frontend/src/lib/auth.tsx`

Replace the **whole file** with this. Read the comments — they explain each
change.

```tsx
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Platform } from 'react-native';
import * as Linking from 'expo-linking';
import * as WebBrowser from 'expo-web-browser';
import type { Session } from '@supabase/supabase-js';
import { getSupabase, supabaseConfigured } from '@/src/lib/supabase-client';

export type AuthUser = {
  user_id: string;
  email: string;
  name: string;
  picture?: string;
};

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

/**
 * Pull the tokens out of the URL the browser hands back.
 *
 * Written by hand rather than with URLSearchParams because React Native's URL
 * polyfill is incomplete and behaves differently across platforms. Supabase
 * puts the tokens in the fragment (`#access_token=...`) for the implicit flow
 * and in the query string for some provider configurations, so check both.
 */
function extractTokens(url: string): { access_token: string; refresh_token: string } | null {
  const hashAt = url.indexOf('#');
  const queryAt = url.indexOf('?');

  const chunks: string[] = [];
  if (hashAt !== -1) chunks.push(url.slice(hashAt + 1));
  if (queryAt !== -1) chunks.push(url.slice(queryAt + 1, hashAt === -1 ? undefined : hashAt));

  for (const chunk of chunks) {
    const params: Record<string, string> = {};
    for (const pair of chunk.split('&')) {
      if (!pair) continue;
      const eq = pair.indexOf('=');
      const key = decodeURIComponent(eq === -1 ? pair : pair.slice(0, eq));
      const value = eq === -1 ? '' : decodeURIComponent(pair.slice(eq + 1).replace(/\+/g, ' '));
      params[key] = value;
    }
    if (params.access_token && params.refresh_token) {
      return { access_token: params.access_token, refresh_token: params.refresh_token };
    }
    // Surface the provider's own error rather than a generic failure.
    if (params.error_description) throw new Error(params.error_description);
    if (params.error) throw new Error(String(params.error));
  }
  return null;
}

function toAuthUser(session: Session): AuthUser {
  const u = session.user;
  return {
    user_id: u.id,
    email: u.email ?? '',
    name: u.user_metadata?.full_name ?? u.email?.split('@')[0] ?? 'User',
    picture: u.user_metadata?.avatar_url,
  };
}

function useAuthState() {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);

  // One subscription to Supabase's own session store replaces the old manual
  // token bootstrap. Supabase reads the persisted session from AsyncStorage,
  // refreshes it if needed, and tells us — so there is no token for us to
  // store, verify or clear ourselves. saveToken/getToken/clearToken are gone.
  useEffect(() => {
    if (!supabaseConfigured) {
      console.warn('[Auth] Supabase env vars missing — staying signed out.');
      setStatus('unauthenticated');
      return;
    }

    let alive = true;
    const supabase = getSupabase();

    const apply = (session: Session | null) => {
      if (!alive) return;
      if (session) {
        setToken(session.access_token);
        setUser(toAuthUser(session));
        setStatus('authenticated');
      } else {
        setToken(null);
        setUser(null);
        setStatus('unauthenticated');
      }
    };

    supabase.auth.getSession()
      .then(({ data }) => apply(data.session))
      .catch(e => {
        console.warn('[Auth] could not read stored session', e);
        if (alive) setStatus('unauthenticated');
      });

    // Fires on sign-in, sign-out, and every token refresh, so `token` in this
    // context is always the live one — important for the backend calls in Part 4.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => apply(session));

    return () => { alive = false; sub.subscription.unsubscribe(); };
  }, []);

  const signInWithGoogle = useCallback(async () => {
    const supabase = getSupabase();
    const redirectTo = Platform.OS === 'web'
      ? window.location.origin + '/'
      : Linking.createURL('/');

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo,
        // On native we open the browser ourselves; on web we let the SDK
        // navigate the page. Setting this on web would leave the user stranded.
        skipBrowserRedirect: Platform.OS !== 'web',
        queryParams: { access_type: 'offline', prompt: 'consent' },
      },
    });
    if (error) throw new Error(error.message);

    // Web: the SDK has already navigated away. When the user comes back,
    // detectSessionInUrl finishes the job and onAuthStateChange fires.
    if (Platform.OS === 'web') return;

    if (!data?.url) throw new Error('Sign-in could not be started. Please try again.');

    // This is the step that was missing entirely. openAuthSessionAsync shows
    // the Google consent screen and resolves when the browser is redirected
    // back to `redirectTo` — handing us that URL.
    const result = await WebBrowser.openAuthSessionAsync(data.url, redirectTo);

    // 'cancel' / 'dismiss' means the user backed out. Not an error.
    if (result.type !== 'success') return;

    const tokens = extractTokens(result.url);
    if (!tokens) throw new Error('Google did not return a session. Please try again.');

    // Hands the tokens to the SDK, which persists them and fires
    // onAuthStateChange — which is what actually flips us to 'authenticated'.
    const { error: setErr } = await supabase.auth.setSession(tokens);
    if (setErr) throw new Error(setErr.message);
  }, []);

  const signOut = useCallback(async () => {
    // Local ledger data is deliberately left alone here — see Part 5.
    const supabase = getSupabase();
    await supabase.auth.signOut();
    // onAuthStateChange clears state, but set it here too so the UI does not
    // sit on a stale "authenticated" frame if the network call is slow.
    setToken(null);
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  return { status, user, token, signInWithGoogle, signOut };
}

type AuthContextValue = ReturnType<typeof useAuthState>;
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const value = useAuthState();
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
```

The exported shape (`status`, `user`, `token`, `signInWithGoogle`, `signOut`) is
unchanged, so no other screen needs editing.

### 1.6 Point `supabase.ts` at the shared client

In `frontend/src/lib/supabase.ts`, delete the local `getClient()` function
(lines 26-37) and the now-unused imports/constants, and import the shared one
instead.

Replace lines 15-37 with:

```ts
import { getSupabase } from '@/src/lib/supabase-client';
import { StorageService } from '@/src/utils/storage/storage-service';
import { toMoney } from '@/src/utils/ledger';
import type { Party, Transaction, Bill, BusinessProfile } from '@/src/mock';
import AsyncStorage from '@react-native-async-storage/async-storage';

const LAST_SYNC_KEY = '@credeasy_last_cloud_sync_v1';

// Alias kept so the two call sites below read unchanged.
const getClient = getSupabase;
```

While you are in this file, delete the stale security comment on lines 8-10 and
replace it:

```ts
 * Security: RLS is enabled on every table (see /docs/supabase-migration.sql).
 * Queries are also filtered by user_id at the application layer as a second
 * layer — but RLS in Postgres is the control that actually enforces isolation.
```

Then typecheck:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx tsc --noEmit
```

Fix anything it reports before continuing. `tsc` printing nothing means success.

### 1.7 Verify sign-in

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx expo start -c
```

Open the app, tap Google sign-in. You should see: browser opens → Google account
picker → consent → browser closes → app shows you as signed in.

**Prove it, don't trust the UI.** In Supabase dashboard → **Authentication →
Users**, your Google account must now appear in the list with a `Last sign in`
timestamp. If the app looks logged in but this table is empty, the session is
fake and you must not proceed.

**Common failures**

| Symptom | Cause |
|---|---|
| `redirect_uri_mismatch` from Google | The URI in 1.2 doesn't exactly match `https://REF.supabase.co/auth/v1/callback`. No trailing slash, `https` not `http`. |
| Browser opens, closes instantly, nothing happens | Your redirect URL isn't in Supabase's allow-list (1.3, step 4). Add `exp://**`. |
| `access_denied` | Add your own Google account under **Test users** on the OAuth consent screen. |
| "Supabase is not configured" | `.env` values missing, or you didn't restart with `-c`. |
| Signed in, but relaunching the app logs you out | `persistSession`/`storage` not set — you're still using an old client somewhere. Grep for `createClient` and make sure it appears only in `supabase-client.ts`. |

**Commit.**

```bash
git add -A && git commit -m "Part 1: complete the Google OAuth round-trip"
```

---

## Part 2 — Fix the database schema so sync can write

**Item fixed:** #2, the UUID mismatch.

### 2.1 What is wrong

`docs/supabase-migration.sql` declares:

```sql
id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
```

but your app generates its own ids that look like this:

```
party-1740412800000-a1b2c3d4
```

That is not a UUID. Postgres rejects it with `invalid input syntax for type
uuid`, so **every** upsert fails. Same for `party_id UUID` in `transactions` and
`bills`.

### 2.2 Which way to fix it

Two options:

| Option | What it means | Verdict |
|---|---|---|
| **A. Change the columns to `TEXT`** | One SQL script. Zero app-code changes. | ✅ **Do this.** |
| B. Make the app generate real UUIDs | Rewrite id generation *and* migrate every existing local id *and* rewrite every reference (`tx.partyId`, `bill.partyId`) on every device already in the wild. | ❌ Far more work, more ways to lose data. |

`user_id` **stays `UUID`** — it has to, because it points at `auth.users(id)`
which is a real UUID. Only your own app-generated ids become `TEXT`.

### 2.3 Check the cloud tables are empty first

Because sync has never succeeded, they should be — but *verify*, don't assume.
Supabase dashboard → **SQL Editor** → New query → run:

```sql
select
  (select count(*) from business_profiles) as profiles,
  (select count(*) from parties)           as parties,
  (select count(*) from transactions)      as transactions,
  (select count(*) from bills)             as bills;
```

**All four must be 0.** If any is non-zero, stop and tell me — the migration
below drops the tables and would delete those rows.

### 2.4 Run the corrected migration

Still in the SQL Editor, run this whole script. It also fixes two real security
gaps in the original policies (explained in Part 3):

```sql
-- CredEasy schema v2
-- Changes from v1:
--   * app-generated ids are TEXT, not UUID (the app does not mint UUIDs)
--   * every UPDATE policy gained WITH CHECK, so a row cannot be reassigned
--     to another user_id
--   * business_profiles gained the missing DELETE policy

begin;

drop view  if exists party_balances;
drop table if exists transactions cascade;
drop table if exists bills        cascade;
drop table if exists parties      cascade;
drop table if exists business_profiles cascade;

-- ---------------------------------------------------------------- profiles
create table business_profiles (
    id          text primary key,
    user_id     uuid not null references auth.users(id) on delete cascade,
    name        text not null default '',
    owner_phone text default '',
    gstin       text default '',
    upi_id      text default '',
    updated_at  timestamptz default now(),
    unique (user_id)
);
alter table business_profiles enable row level security;

create policy "profiles_select" on business_profiles for select
    using (auth.uid() = user_id);
create policy "profiles_insert" on business_profiles for insert
    with check (auth.uid() = user_id);
create policy "profiles_update" on business_profiles for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "profiles_delete" on business_profiles for delete
    using (auth.uid() = user_id);

-- ----------------------------------------------------------------- parties
create table parties (
    id              text primary key,
    user_id         uuid not null references auth.users(id) on delete cascade,
    name            text not null,
    phone           text default '',
    photo_uri       text,
    type            text not null check (type in ('CUSTOMER', 'SUPPLIER')),
    opening_balance numeric(15, 2) not null default 0,
    created_at      timestamptz not null default now()
);
create index idx_parties_user_id on parties(user_id);
alter table parties enable row level security;

create policy "parties_select" on parties for select
    using (auth.uid() = user_id);
create policy "parties_insert" on parties for insert
    with check (auth.uid() = user_id);
create policy "parties_update" on parties for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "parties_delete" on parties for delete
    using (auth.uid() = user_id);

-- ------------------------------------------------------------ transactions
create table transactions (
    id          text primary key,
    user_id     uuid not null references auth.users(id) on delete cascade,
    party_id    text not null references parties(id) on delete cascade,
    amount      numeric(15, 2) not null,
    type        text not null check (type in ('DEBIT', 'CREDIT')),
    note        text default '',
    photo_uri   text,
    date        timestamptz not null,
    sync_status text default 'SYNCED' check (sync_status in ('SYNCED', 'PENDING')),
    created_at  timestamptz default now()
);
create index idx_transactions_user_id  on transactions(user_id);
create index idx_transactions_party_id on transactions(party_id);
create index idx_transactions_date     on transactions(date desc);
alter table transactions enable row level security;

create policy "tx_select" on transactions for select
    using (auth.uid() = user_id);
create policy "tx_insert" on transactions for insert
    with check (auth.uid() = user_id);
create policy "tx_update" on transactions for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "tx_delete" on transactions for delete
    using (auth.uid() = user_id);

-- ------------------------------------------------------------------- bills
create table bills (
    id             text primary key,
    user_id        uuid not null references auth.users(id) on delete cascade,
    party_id       text not null references parties(id) on delete cascade,
    items          jsonb not null default '[]',
    gst_applicable boolean not null default false,
    total          numeric(15, 2) not null,
    status         text default 'UNPAID' check (status in ('UNPAID', 'PAID')),
    created_at     timestamptz default now()
);
create index idx_bills_user_id  on bills(user_id);
create index idx_bills_party_id on bills(party_id);
alter table bills enable row level security;

create policy "bills_select" on bills for select
    using (auth.uid() = user_id);
create policy "bills_insert" on bills for insert
    with check (auth.uid() = user_id);
create policy "bills_update" on bills for update
    using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "bills_delete" on bills for delete
    using (auth.uid() = user_id);

-- ------------------------------------------------------- balances (view)
-- Same sign convention as src/utils/ledger.ts:
--   balance = opening + Σ DEBIT − Σ CREDIT
--   > 0  →  "You'll Get"   < 0  →  "You'll Give"
create or replace view party_balances as
select
    p.id      as party_id,
    p.user_id,
    p.name,
    p.phone,
    p.type,
    p.opening_balance,
    coalesce(sum(case when t.type = 'DEBIT'  then  t.amount
                      when t.type = 'CREDIT' then -t.amount
                      else 0 end), 0) as net_transactions,
    p.opening_balance
      + coalesce(sum(case when t.type = 'DEBIT'  then  t.amount
                          when t.type = 'CREDIT' then -t.amount
                          else 0 end), 0) as current_balance
from parties p
left join transactions t on t.party_id = p.id
group by p.id, p.user_id, p.name, p.phone, p.type, p.opening_balance;

-- security_invoker makes the view respect the *caller's* RLS instead of the
-- view owner's. Without it the view is a hole straight through your policies.
alter view party_balances set (security_invoker = true);

commit;
```

Save this over `docs/supabase-migration.sql` too, so the file and the live
database agree.

### 2.5 Verify sync round-trips

This is the moment of truth for the whole exercise.

1. In the app, signed in, add a party and a transaction.
2. Trigger a sync (Settings → whatever the sync/backup button is).
3. Supabase → **Table Editor → parties**. Your party must be there, with a
   `user_id` matching your row in Authentication → Users.
4. Now prove the *pull* direction: uninstall the app (or clear its data), reinstall,
   sign in with the same Google account. Your party and transaction must come back.

Only when step 4 works has sync ever actually worked. **Note the date you got
here** — Part 5 depends on it.

**If push fails**, the error message tells you which column. Read it literally:
- `invalid input syntax for type uuid` → you missed a `text` somewhere in 2.4.
- `violates foreign key constraint` on `party_id` → a transaction refers to a
  party that isn't in the cloud. Push parties before transactions (the existing
  code already does).
- `violates row-level security policy` → you are not actually signed in. Go back
  to Part 1 and re-verify with the Users table.
- `null value in column "total" violates not-null` → a bill has a NaN total.
  (I already routed this through `toMoney`, so this shouldn't happen.)

**Commit.**

```bash
git add -A && git commit -m "Part 2: TEXT ids, WITH CHECK on updates, sync verified"
```

---

## Part 3 — Confirm RLS is really protecting you

**Item fixed:** #1.

Part 2 already ran the `enable row level security` statements and the corrected
policies. This part is about *proving* it, because RLS silently failing open is
the worst-case outcome and it looks identical to everything working.

### 3.1 Understand what you're checking

- `auth.uid()` is a function inside Postgres that returns the user id from the
  JWT on the current request. With no JWT it returns `NULL`, and `NULL = user_id`
  is never true, so **an unauthenticated request sees zero rows.** That's the
  behaviour you want.
- `using (...)` controls *which existing rows you may see or touch*.
- `with check (...)` controls *what a row is allowed to look like after you write
  it*. The original SQL had `using` but no `with check` on every UPDATE — meaning
  a signed-in user could take their own row and set `user_id` to somebody else's
  id, writing data into another person's account. Part 2 fixed that.

### 3.2 Check for tables with RLS off

SQL Editor:

```sql
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
order by tablename;
```

`rowsecurity` must be `true` for every row. If a table shows `false`:

```sql
alter table public.THAT_TABLE enable row level security;
```

Also check that every table has at least one policy — RLS on with *no* policies
denies everything, which will look like "sync broke again":

```sql
select tablename, count(*) as policies
from pg_policies
where schemaname = 'public'
group by tablename
order by tablename;
```

You should see 4 policies each for `business_profiles`, `parties`,
`transactions`, `bills`.

### 3.3 Prove isolation with a second account

The only test that counts.

1. Sign in to the app with **Google account A**. Add a party named `AAA-TEST`. Sync.
2. Sign out. Sign in with **Google account B** (any second Google account).
3. Sync / pull.

**Account B must not see `AAA-TEST`.** If it does, RLS is not working — stop and
recheck 3.2 before shipping anything.

You can also check from the dashboard side. Supabase → SQL Editor:

```sql
-- Runs as an unauthenticated client. Should return 0.
set local role anon;
select count(*) from parties;
reset role;
```

### 3.4 Two more dashboard settings worth 60 seconds

- **Authentication → Policies**: skim it. Anything marked with a warning triangle
  is a table Supabase thinks is exposed.
- **Project Settings → API**: confirm you are copying the `anon` `public` key
  into `frontend/.env`, **not** `service_role`. If `service_role` ever went into
  the frontend, click **Reveal → Generate new secret** to rotate it immediately —
  that key bypasses RLS entirely.

**Commit.**

---

## Part 4 — Make the backend accept the app's token

**Item fixed:** #3, the two-token-systems problem (the voice assistant 401s).

### 4.1 What is wrong

You have two unrelated login systems:

- The **app** holds a Supabase JWT (a long `eyJ...` string).
- **`backend/server.py`** issues its own `st_...` token from `/api/auth/session`
  and looks it up in MongoDB collections `users` and `user_sessions`.

The app never calls `/api/auth/session`, and the backend has never heard of a
Supabase JWT. So every authenticated backend route rejects every request.

The fix: **delete the backend's parallel login system** and have it verify the
Supabase JWT instead. One source of truth. No new Python dependency — `httpx` is
already in `requirements.txt`.

### 4.2 Add the backend's Supabase config

Add to `backend/.env`:

```
SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

Same values as the frontend. (The anon key is public, so this is not a secret
leak — the backend just needs it as the `apikey` header Supabase requires.)

### 4.3 Replace the auth dependency in `backend/server.py`

Near the top, next to the other config reads, add:

```python
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
```

Then replace the entire body of `get_authenticated_user` with:

```python
async def get_authenticated_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Verify the caller's Supabase access token.

    Replaces the previous st_... session tokens stored in Mongo. The app has
    always held a Supabase JWT and never called /api/auth/session, so the two
    systems could never agree; asking Supabase to validate its own token
    removes the second system entirely.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        # A misconfigured server must not look like a rejected user.
        logger.error("SUPABASE_URL / SUPABASE_ANON_KEY are not configured")
        raise HTTPException(status_code=500, detail="Authentication is not configured on the server")

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as http:
            resp = await http.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
            )
    except Exception:
        # Distinguish "we could not check" from "the token is bad", so a network
        # blip does not silently sign the shopkeeper out.
        logger.exception("Supabase token verification request failed")
        raise HTTPException(status_code=503, detail="Could not verify your session. Please try again.")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    try:
        data = resp.json()
    except ValueError:
        logger.error("Supabase /auth/v1/user returned a non-JSON body")
        raise HTTPException(status_code=502, detail="Could not verify your session. Please try again.")

    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    metadata = data.get("user_metadata") or {}
    return {
        "user_id": str(user_id),
        "email": data.get("email") or "",
        "name": metadata.get("full_name") or metadata.get("name") or "",
        "picture": metadata.get("avatar_url"),
    }
```

Then delete the now-dead code:

- the `POST /api/auth/session` endpoint and its `AuthSessionRequest` model
- `SESSION_TTL_DAYS` and anything referencing `db.user_sessions`
- the `db.user_sessions` / `db.users` index creation inside `lifespan` (keep the
  `try/except` wrapper if other indexes remain)
- the `DuplicateKeyError` import if nothing else uses it

Sanity check for leftovers:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/backend" && grep -rn "user_sessions\|SESSION_TTL_DAYS\|auth/session\|DuplicateKeyError" . --include=*.py
```

Then:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/backend" && python -m flake8 --select=E9,F server.py
```

`E9,F` catches syntax errors and undefined/unused names — exactly the mistakes
that deleting code causes. No output means clean.

### 4.4 Update the tests

`backend/tests/test_auth.py` has a `TestAuthSession` class with 3 tests hitting
the endpoint you just deleted. Those tests will fail — **that's correct
behaviour, not a bug to work around.** Replace that class with tests for the new
dependency. `FakeCollection` and the rest of the file stay as they are.

```python
class TestSupabaseTokenAuth:
    """The Authorization header is now a Supabase access token, verified by
    calling Supabase. We stub that call so the tests stay offline."""

    def _client(self, monkeypatch):
        monkeypatch.setattr(server, "SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setattr(server, "SUPABASE_ANON_KEY", "test-anon-key")
        return TestClient(server.app)

    def _stub(self, monkeypatch, status_code, payload):
        class FakeResponse:
            def __init__(self):
                self.status_code = status_code
            def json(self):
                return payload

        async def fake_get(self, url, **kwargs):
            return FakeResponse()

        monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    def test_missing_header_is_rejected(self, monkeypatch):
        client = self._client(monkeypatch)
        resp = client.post("/api/status", json={"client_name": "x"})
        assert resp.status_code == 401

    def test_malformed_header_is_rejected(self, monkeypatch):
        client = self._client(monkeypatch)
        resp = client.post(
            "/api/status",
            json={"client_name": "x"},
            headers={"Authorization": "NotBearer abc"},
        )
        assert resp.status_code == 401

    def test_token_supabase_rejects_is_rejected(self, monkeypatch):
        self._stub(monkeypatch, 401, {"msg": "invalid claim"})
        client = self._client(monkeypatch)
        resp = client.post(
            "/api/status",
            json={"client_name": "x"},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp.status_code == 401

    def test_unconfigured_server_does_not_look_like_a_bad_token(self, monkeypatch):
        monkeypatch.setattr(server, "SUPABASE_URL", "")
        monkeypatch.setattr(server, "SUPABASE_ANON_KEY", "")
        client = TestClient(server.app)
        resp = client.post(
            "/api/status",
            json={"client_name": "x"},
            headers={"Authorization": "Bearer anything"},
        )
        assert resp.status_code == 500
```

Run them:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/backend" && python -m pytest
```

Do **not** edit `pytest.ini` — it carries an explicit note not to change
`addopts`.

### 4.5 Send the token from the app

`frontend/app/voice-assistant.tsx` calls the backend twice with no auth header.
Both need one.

At the top of the component, alongside the other hooks:

```tsx
import { useAuth } from '@/src/lib/auth';
// ...
const { token } = useAuth();
```

**Line ~195**, the `/api/voice/assist` call:

```tsx
      if (!token) throw new Error(hi ? 'कृपया पहले साइन इन करें।' : 'Please sign in first.');
      const resp = await fetch(`${API}/api/voice/assist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ transcript, context: buildContext(), lang }),
      });
```

**Line ~263**, the `/api/voice/transcribe` call. Note: set **only**
`Authorization` — do not set `Content-Type` on a `FormData` body, or you will
overwrite the multipart boundary the browser generates and the upload will fail
with a confusing parse error:

```tsx
      if (!token) throw new Error(hi ? 'कृपया पहले साइन इन करें।' : 'Please sign in first.');
      const resp = await fetch(`${API}/api/voice/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
```

Because `token` comes from `onAuthStateChange`, it is refreshed automatically and
you never have to think about expiry.

### 4.6 Verify

Start the backend:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/backend" && python -m uvicorn server:app --reload --port 8000
```

Then, signed in, use the voice assistant. It should transcribe and reply. Watch
the uvicorn log — you want `200`, not `401`.

Confirm the door is actually locked, from a separate terminal:

```bash
curl -i -X POST "http://localhost:8000/api/voice/assist" -H "Content-Type: application/json" -d "{\"transcript\":\"hello\"}"
```

That must return **401**. If it returns 200, the route is missing its
`Depends(get_authenticated_user)`.

### 4.7 Optional follow-up

After this, MongoDB is only used by the `status_checks` demo collection. You can
likely drop Mongo (and `motor`/`pymongo`) entirely — but that's cleanup, not a
fix. Leave it for later.

**Commit.**

```bash
git add -A && git commit -m "Part 4: backend verifies Supabase JWTs; drop parallel session system"
```

---

## Part 5 — Handle sign-out without destroying data

**Item fixed:** #4.

### 5.1 Why this waited until now

Currently sign-out leaves all local ledger data on the device. That's a
cross-account leak: sign out, hand the phone to someone else, they sign in with
their account and see the previous user's customers.

The obvious fix — clear local data on sign-out — was **wrong to do earlier**,
because sync had never worked, so AsyncStorage was the *only* copy of the
shopkeeper's ledger. Clearing it would have permanently destroyed real business
records.

**Gate this part behind Part 2.5 step 4.** If you have not personally watched
data come back onto a fresh install, do not enable clearing.

### 5.2 The rule

> Never clear local data unless a push to the cloud has just succeeded.

### 5.3 Implement it

In `frontend/src/lib/auth.tsx`, replace `signOut` with:

```tsx
  const signOut = useCallback(async (options?: { clearLocalData?: boolean }) => {
    const supabase = getSupabase();

    if (options?.clearLocalData) {
      if (!user?.user_id) throw new Error('Not signed in.');
      // Push BEFORE clearing, and only clear if the server accepted everything.
      // Clearing first, or clearing after a partial push, destroys the only
      // copy of the ledger — this app was offline-first long before sync worked.
      const { error } = await CloudSync.pushToCloud(user.user_id);
      if (error) {
        throw new Error(
          'Your data could not be backed up, so nothing was deleted. ' +
          'Check your connection and try again. (' + error + ')'
        );
      }
      await StorageService.clearAllLedgerData();
    }

    await supabase.auth.signOut();
    setToken(null);
    setUser(null);
    setStatus('unauthenticated');
  }, [user]);
```

Add the imports at the top of `auth.tsx`:

```tsx
import { CloudSync } from '@/src/lib/supabase';
import { StorageService } from '@/src/utils/storage/storage-service';
```

If `StorageService.clearAllLedgerData()` doesn't exist, add it — clearing only
the ledger keys, never `AsyncStorage.clear()`, which would also wipe the trial
start date and onboarding flag:

```ts
  /** Removes ledger data only. Deliberately not AsyncStorage.clear(): that
   *  would also delete the trial start date and the onboarding flag, silently
   *  restarting the free trial and the setup wizard. */
  async clearAllLedgerData(): Promise<void> {
    await AsyncStorage.multiRemove([
      PARTIES_KEY,
      TRANSACTIONS_KEY,
      BILLS_KEY,
      BUSINESS_PROFILE_KEY,
    ]);
  },
```

(Use whatever the real key constant names are in that file.)

### 5.4 Ask the user, don't decide for them

In your settings screen, where sign-out is triggered:

```tsx
  const handleSignOut = () => {
    Alert.alert(
      'Sign out',
      'Do you want to remove this business\'s data from this phone? ' +
      'It will be backed up to your account first, and restored when you sign in again.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Keep data on phone', onPress: () => signOut() },
        {
          text: 'Back up and remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await signOut({ clearLocalData: true });
            } catch (e: any) {
              Alert.alert('Not signed out', e?.message ?? 'Please try again.');
            }
          },
        },
      ],
    );
  };
```

### 5.5 Verify

1. Sign in as A, add a party, choose **Back up and remove**. → App is empty.
2. Sign in as B. → B sees nothing of A's. ✅ leak closed.
3. Sign out B, sign in as A again. → A's party comes back. ✅ nothing lost.
4. Turn on airplane mode, sign in as A, choose **Back up and remove**. → You get
   the "could not be backed up, nothing was deleted" error and the data is
   **still there**. ✅ the guard works.

Step 4 is the one that matters most. Do not skip it.

**Commit.**

---

## Part 6 — Get ads actually rendering

**Item fixed:** #5.

### 6.1 What is wrong

`src/components/ads/BasicBanner.native.tsx` is a deliberate no-op because
`react-native-google-mobile-ads` is not installed. The Basic tier promises ads
and shows none.

**Read this before you start:** ads **cannot** work in Expo Go. The library needs
native code. You must make a *development build*. That's a real, slow step — plan
for it.

### 6.2 Set up AdMob

1. <https://apps.admob.com> → create an account (needs a payment profile).
2. **Apps → Add app** → Android → not listed on Play yet (if so) → name `CredEasy`.
3. Copy the **App ID**, format `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY` (note the
   **`~`**).
4. **Ad units → Add ad unit → Banner** → name it `CredEasy Basic Banner`. Copy the
   **Ad unit ID**, format `ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ` (note the **`/`**).
5. Repeat 2-4 for iOS if you're shipping there. The App IDs differ per platform.

The audit found a unit id already referenced in the code:
`ca-app-pub-7375403009647887/8719033584`. If that's yours, use it. If it came
from a template, **replace it** — serving ads on someone else's unit id is not
something you want to do.

### 6.3 Install and configure

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx expo install react-native-google-mobile-ads
```

Use `npx expo install`, not `yarn add` — it picks the version compatible with
your Expo SDK.

Then in `frontend/app.json`, add to the `plugins` array (keep the existing
entries):

```json
    [
      "react-native-google-mobile-ads",
      {
        "androidAppId": "ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY",
        "iosAppId": "ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY"
      }
    ]
```

Use the **App ID** (with `~`) here, not the ad unit id. Mixing them up is the
single most common cause of "the app crashes on launch after adding AdMob".

### 6.4 Restore the banner

`frontend/src/components/ads/BasicBanner.native.tsx`:

```tsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import {
  BannerAd,
  BannerAdSize,
  TestIds,
} from 'react-native-google-mobile-ads';

// Real ad units must never be requested from a dev build. Google treats it as
// invalid traffic and can suspend the AdMob account.
const UNIT_ID = __DEV__ ? TestIds.BANNER : 'ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ';

export default function BasicBanner() {
  return (
    <View style={styles.wrap}>
      <BannerAd
        unitId={UNIT_ID}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: true }}
        onAdFailedToLoad={e => console.warn('[Ads] banner failed to load', e)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: 'center', justifyContent: 'center' },
});
```

Keep whatever `BasicBanner.web.tsx` / `BasicBanner.tsx` fallback exists — Metro
picks `.native.tsx` on device and the other on web, and the web build must not
try to import the native module.

### 6.5 Build natively

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx expo prebuild --clean
```

This generates the `android/` and `ios/` folders from `app.json`. `--clean`
regenerates them, so **any hand-edits you made in those folders are lost** —
that's fine here because you haven't made any.

Then, with an Android device plugged in (USB debugging on) or an emulator running:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx expo run:android
```

First run downloads Gradle and takes 10-30 minutes. Later runs are fast. You need
Android Studio installed for the SDK; if the build complains about
`ANDROID_HOME`, that's what's missing.

Alternatively use EAS (builds in the cloud, no Android Studio needed):

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend" && npx eas build --profile development --platform android
```

### 6.6 Verify

Run the app on the device as a **Basic** tier user. You should see a Google test
banner ("Test Ad") at the bottom. Test ads always fill; real ads often don't
immediately after account creation, which is why `TestIds` in dev matters.

Also verify ads are *absent* for adfree/premium tiers — the `showAds` flag in
`src/lib/revenuecat.tsx` already computes this.

**Commit.** (`android/` and `ios/` are generated — add them to `.gitignore`
rather than committing them, unless you start hand-editing native code.)

---

## Part 7 — Decide what web users see

**Item fixed:** #6.

### 7.1 What's happening

`frontend/src/lib/revenuecat.tsx:16`:

```ts
export const rcEnabled = Platform.OS !== 'web' || __DEV__;
```

In a **production web** build that's `false`, so both RevenueCat queries are
disabled and nothing is ever purchasable. Web users see a paywall they cannot
pass.

This is not a bug I could fix for you — it's a product decision. Pick one:

### Option A — Web is view-only, subscribe in the app (recommended)

Simplest, and honest. On web, replace the paywall with "Subscriptions are managed
in the CredEasy mobile app" plus store links.

In your paywall screen:

```tsx
import { Platform } from 'react-native';
import { rcEnabled } from '@/src/lib/revenuecat';

if (!rcEnabled) {
  return (
    <View style={styles.center}>
      <Text style={styles.title}>Subscribe in the app</Text>
      <Text style={styles.body}>
        Plans are managed through the CredEasy mobile app. Install it and sign in
        with the same Google account — your ledger is already there.
      </Text>
      {/* Play Store / App Store buttons */}
    </View>
  );
}
```

One caveat: Apple and Google restrict linking out to external payment from
*inside* the app. Linking from your **website** to the *stores* is fine. Don't
copy this block into the native paywall.

### Option B — Enable RevenueCat Web Billing

Real web purchases. More work: set up Web Billing in the RevenueCat dashboard,
connect Stripe, get a web-specific public key, and change line 16 to
`export const rcEnabled = true;` with `getRevenueCatApiKey()` returning the web
key for `Platform.OS === 'web'`. Only worth it if web is a real sales channel.

Whichever you choose, also revisit line 17:

```ts
export const isPreviewFallbackAllowed = __DEV__ || Platform.OS === 'web';
```

That `|| Platform.OS === 'web'` lets **production web** fall into the *simulated*
plans path, where "purchasing" just writes a fake tier to local storage. Under
Option A it's unreachable (because `rcEnabled` is false, so the queries never
run), but it is a live footgun the moment you flip `rcEnabled`. Tighten it to:

```ts
export const isPreviewFallbackAllowed = __DEV__;
```

---

## Final checklist before you ship

```
[ ] git repo initialised, .env files gitignored, everything committed
[ ] Google account appears in Supabase → Authentication → Users after sign-in
[ ] App stays signed in across a full app restart
[ ] Party added on device appears in Supabase → Table Editor → parties
[ ] Fresh install + sign-in restores parties, transactions, bills and profile
[ ] pg_tables shows rowsecurity = true for all four tables
[ ] Account B cannot see account A's data
[ ] curl without a token returns 401 from every /api route
[ ] Voice assistant works signed in, fails cleanly signed out
[ ] Airplane-mode sign-out-and-clear refuses to delete anything
[ ] Test banner shows for Basic tier on a real device build
[ ] No ads for adfree/premium
[ ] service_role key appears nowhere under frontend/
[ ] npx tsc --noEmit is clean
[ ] python -m pytest is green
```

---

## Where to look when something breaks

| Where | How |
|---|---|
| App JS errors | The terminal running `npx expo start`, plus the in-app red screen |
| Native crashes (Android) | `npx react-native log-android`, or `adb logcat *:E` |
| Supabase auth | Dashboard → **Logs → Auth Logs** — shows every rejected login and why |
| Supabase queries / RLS denials | Dashboard → **Logs → Postgres Logs** |
| Backend | The uvicorn terminal. Every handler already calls `logger.exception` on failure, so the real traceback is there even though the API returns a generic message |

One habit worth forming: when something fails, find the *first* error, not the
loudest one. A single failed sign-in produces a dozen downstream errors, and only
the first one tells you anything.
