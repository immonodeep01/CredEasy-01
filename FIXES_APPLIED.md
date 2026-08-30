# Fixes Applied Following the Fixing Guide

## Summary
This document summarizes the code fixes that have been applied to align with the CredEasy Fixing Guide, and identifies what still requires user intervention.

## Fixes Applied

### Part 5.3 - Sign-Out with Local Data Backup
**File:** `frontend/src/lib/auth.tsx`

**Changes made:**
1. Added imports:
   ```ts
   import { CloudSync } from '@/src/lib/supabase';
   import { StorageService } from '@/src/utils/storage/storage-service';
   ```
2. Updated `signOut` function to accept `clearLocalData` option:
   ```ts
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
           'Your data could not be backed up, so nothing was deleted. '
           + 'Check your connection and try again. (' + error + ')'
         );
       }
       await StorageService.clearAllLedgerData();
     }

     await supabase.auth.signOut();
     // onAuthStateChange clears state, but set it here too so the UI does not
     // sit on a stale "authenticated" frame if the network call is slow.
     setToken(null);
     setUser(null);
     setStatus('unauthenticated');
   }, [user]);
   ```

**Status:** ✅ COMPLETED - The settings screen's "Back up and remove" option will now work correctly.

## What Still Requires Your Help

### 1. Database Migration (Part 2.4) - ✅ DONE
**Status:** You've completed the database migration. The four tables (`business_profiles`, `parties`, `transactions`, `bills`) now exist in your Supabase project with the correct schema (TEXT ids for app-generated IDs, proper RLS policies with WITH CHECK, etc.).

**Verify:** Re-run the Part 2.3 check query:
```sql
select
  (select count(*) from business_profiles) as profiles,
  (select count(*) from parties)           as parties,
  (select count(*) from transactions)      as transactions,
  (select count(*) from bills)             as bills;
```
This should return `0, 0, 0, 0` confirming tables exist and are empty.

### 2. AdMob Configuration (Part 6) - ✅ DONE
**Your AdMob App ID:** `ca-app-pub-7375403009647887~5294793896`

**Files Updated:**
- **`frontend/app.json`** — Added `react-native-google-mobile-ads` plugin with your Android and iOS App IDs
- **`frontend/src/components/ads/BasicBanner.native.tsx`** — Restored the actual banner component using `BannerAd` from `react-native-google-mobile-ads`

**Note:** The ad unit ID (`ca-app-pub-7375403009647887/8719033584`) is from the existing code. If this is not your own ad unit, replace it in `BasicBanner.native.tsx` — go to AdMob → Apps → Ad units → Add ad unit → Banner, and swap in your own.

**Remaining Step:** `npx expo install react-native-google-mobile-ads` if not already installed, then build a native development build (`npx expo run:android` or `npx eas build --profile development --platform android`) — ads don't render in Expo Go.

### 3. RevenueCat/Web Billing Decision (Part 7)
**File:** `frontend/src/lib/revenuecat.tsx`

**Decision Required:** Choose between:
- **Option A (Recommended):** Web is view-only - modify paywall to show "Subscriptions are managed in the CredEasy mobile app"
- **Option B:** Enable RevenueCat Web Billing - requires Stripe setup and web-specific API key

**Current line 16:** `export const rcEnabled = Platform.OS !== 'web' || __DEV__;`

**If choosing Option A:** Modify your paywall screen to show subscription guidance for web users.

### 4. Environment Variables
Verify these are set correctly in `.env` files:
- `frontend/.env`: `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- `backend/.env`: `SUPABASE_URL` and `SUPABASE_ANON_KEY` (same values as frontend)

## Verification Checklist After Completing Items Above

After completing the database migration and your configuration tasks, verify:

- [ ] Google account appears in Supabase → Authentication → Users after sign-in
- [ ] App stays signed in across a full app restart  
- [ ] Party added on device appears in Supabase → Table Editor → parties
- [ ] Fresh install + sign-in restores parties, transactions, bills and profile
- [ ] `pg_tables` shows `rowsecurity = true` for all four tables
- [ ] Account B cannot see account A's data (test with second Google account)
- [ ] Backend `/api` routes return 401 without valid Authorization header
- [ ] Voice assistant works when signed in, fails cleanly when signed out
- [ ] Airplane-mode sign-out with "Back up and remove" preserves data
- [ ] Test banner shows for Basic tier on real device build
- [ ] No ads showing for adfree/premium tiers

## Next Steps
1. ✅ Database migration completed
2. ✅ AdMob configured (app.json + BasicBanner.native.tsx)
3. **Then:** Make web billing decision (Part 7)
4. **Finally:** Run through the verification checklist above

Each major part should be committed separately as you complete it:
```bash
git add -A && git commit -m "Part 2: Migration applied"
git add -A && git commit -m "Part 5: Sign-out clears local data after backup"
git add -A && git commit -m "Part 6: AdMob configured"
```