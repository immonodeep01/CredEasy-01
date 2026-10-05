# Google Play Store Submission Guide

This guide lists every step required to ship CredEasy to the Google Play Store. Steps marked **🟢 automatic** are already done in this repo. Steps marked **🟡 TODO** must be completed by you (the developer) before submission — they involve accounts, credentials, or hosted assets that cannot be automated from this terminal.

---

## 1. Pre-Flight Checklist

### 1.1 Store listing assets (🟡 TODO)

The app already has CredEasy branding and three privacy-redacted portrait
screenshots in `website/assets/`. Prepare and upload the store listing assets
in Play Console:

| Asset | Dimensions | Format | Notes |
|---|---|---|---|
| App icon | 512 × 512 px | PNG (no transparency) | Export an opaque, exact-size store icon from the current CredEasy mark |
| Feature graphic | **1024 × 500 px** | PNG or JPEG | **Required** for Play Store listing |
| Phone screenshots | minimum 2, up to 8 | PNG or JPEG | Existing product screenshots are 720 × 1600; verify they accurately show current shipped UI |
| 7-inch tablet screenshots | 0 to 8 | PNG or JPEG | Optional but recommended |
| 10-inch tablet screenshots | 0 to 8 | PNG or JPEG | Optional but recommended |

The adaptive icon and splash image are runtime Android assets, not Play Store
listing uploads. Keep them as separate resources.

The required 1024 × 500 feature graphic is not present in the current Play
listing assets. Upload a suitable feature graphic before publishing.

### 1.2 Permissions audit (🟡 verify generated release manifest)

The app config declares the permissions used by current features:

- `RECORD_AUDIO` — voice assistant
- `USE_BIOMETRIC` / `USE_FINGERPRINT` — app lock
- `MODIFY_AUDIO_SETTINGS` — voice assistant
- `READ_CONTACTS` — pick a customer from the system address book

`app.json` blocks legacy external-storage, contacts-write, and overlay
permissions because the app only reads contacts, uses the system document/photo
pickers, and does not draw over other apps. Check the merged release manifest
after every native dependency or Expo prebuild change; dependency manifests can
reintroduce permissions. Camera capture in party/transaction attachments,
microphone access, notifications for the widget, and Google Mobile Ads' ad ID
remain declared for the features that use them. Do not block a permission
without rechecking the matching feature on supported Android versions.

### 1.3 Code and tooling (🟢 automatic)

- Frontend TypeScript check passes.
- Frontend ESLint reports zero errors; existing warnings remain.
- The built artifact currently targets Android 16 (API 36), the current minimum for new mobile submissions as of August 31, 2026.
- `eas.json` `production` profile requests an Android App Bundle with `developmentClient: false`.
- Local Gradle release builds are signed with the debug keystore and are QA-only. Configure EAS production signing before upload.
- A universal local QA APK previously measured about 132.6 MB. Building only the arm64 ABI produces about 53.3 MB, a 59.8% reduction. The latest local APK is 53,289,064 bytes (SHA-256 `2C2212A039F546ACFAF369EDBBA31686AE386025E163B2872AE82C84EA419948`) and contains only `arm64-v8a`; it will not install on 32-bit-only devices. Use the production AAB profile for Play so Google Play can generate device-specific downloads.
- `npm audit --omit=dev --audit-level=high` currently fails with reported transitive high-severity advisories. Review and resolve or formally assess these without forcing Expo/React Native major upgrades.
- Verify the public privacy-policy URL, Play listing content, store screenshots, feature graphic, ads declaration, Data safety form, and data-deletion responses in Play Console before production submission.

### 1.4 Security review

The security review found one medium-severity issue: the headless Chotu widget
could previously read saved ledger context and confirm writes while App Lock was
enabled. The widget now fails closed when lock status cannot be read, blocks
assistant and confirmation actions while App Lock is enabled, stops active
microphone capture, clears stored widget results for each placed widget, and
refreshes widget instances both when lock is enabled and on app startup.

App Lock intentionally disables Chotu widget functionality even after the user
unlocks the main app; there is no shared headless-safe unlocked-state signal.
Users must disable App Lock in CredEasy to use Chotu from the widget. This
restriction avoids exposing ledger data outside the locked app.

### 1.5 Account deletion requirement (🟡 TODO)

CredEasy's first Google OAuth sign-in creates a Supabase user account. Google
Play's account-deletion rule therefore applies: provide both an in-app account
deletion path (or an in-app link to the deletion web resource) and a public web
resource where users can request deletion of the account and associated data.
The current Settings navigation intentionally does not expose account
deletion, and no public deletion-request resource has been verified. This is a
production-submission blocker until both are implemented/deployed and tested.
Complete Play Console's data-deletion questions as well.

---

## 2. Privacy Policy (website page created; publishing still required)

The marketing site now includes `website/privacy-policy.html` and `website/terms-and-conditions.html`, linked from its footer. After deploying the website to the domain you control, confirm the public URLs load and use the privacy-policy URL in the Play Console. Do not submit a local file URL or an unpublished URL.

---

## 3. Release Keystore (🟡 TODO — CRITICAL)

The current `android/app/build.gradle` is set up to use the **debug** keystore for release builds. Google Play **will reject** any APK/AAB signed with the debug key. This must be fixed before shipping.

### 3.1 Generate the keystore

Run once, on a machine that is not committed to git:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend/android/app"
keytool -genkeypair -v -storetype PKCS12 \
  -keystore release.keystore \
  -alias credeasy \
  -keyalg RSA -keysize 2048 -validity 10000
```

Answer the prompts (CN = your company name, O = CredEasy, C = your country). Set strong passwords and **save them** in a password manager — losing the keystore means losing the ability to update the app.

### 3.2 Wire it into Gradle

Open `frontend/android/app/build.gradle`. The `signingConfigs` block already has a commented-out `release` config. Uncomment it and replace the placeholder passwords. The recommended way is to read them from environment variables so the build does not depend on values in `gradle.properties`:

```groovy
release {
    storeFile file('release.keystore')
    storePassword System.getenv("CREDEASY_KEYSTORE_PASSWORD") ?: "REPLACE_ME"
    keyAlias 'credeasy'
    keyPassword System.getenv("CREDEASY_KEY_PASSWORD") ?: "REPLACE_ME"
}
```

Then in the `buildTypes.release` block, replace `signingConfig signingConfigs.debug` with `signingConfig signingConfigs.release`.

### 3.3 Confirm the keystore is gitignored

`release.keystore` and any `*.jks` files must not be committed. The current `.gitignore` does not exclude them; add a line to the root `.gitignore`:

```
# Android release signing
*.jks
*.keystore
!debug.keystore
```

(Keep the `debug.keystore` excluded so the only committed one is the well-known Expo default — actually **delete** the rule and just exclude all keystores to be safe.)

### 3.4 Upload to Play Console

In Google Play Console → **Setup → App signing**, upload your release keystore. This lets Google re-sign your app with their own key, so a lost keystore doesn't lock you out of updating the app.

---

## 4. AdMob Account (🟡 TODO)

`app.json` currently uses Google's test AdMob App IDs and native ad units are
intentionally configured as test inventory by project requirement. This is
safe for QA but is not monetized production advertising. Declare ads accurately
in Play Console if ads are displayed. Do not substitute live ad IDs without a
separate product decision; if production monetization is later enabled, verify
the owned AdMob App IDs and policy declarations with the account owner.

If you have not set up an AdMob account:

1. Go to <https://apps.admob.com> and create an account (Google Play developer account payment profile is required).
2. **Apps → Add app → Android → not listed on Play yet** → name `CredEasy`.
3. Copy the App ID (format `ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY` — note the `~`).
4. **Ad units → Add ad unit → Banner** → name `CredEasy Basic Banner`. Copy the Ad unit ID (format `ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ` — note the `/`).
5. Update `frontend/src/components/ads/BasicBanner.native.tsx` line 16 — replace `PROD_AD_UNIT_ID` with the new unit ID.
6. Repeat for iOS if you plan to ship there.

**Caution:** AdMob has strict rules about using real ad unit IDs in development. The `__DEV__ ? TestIds.BANNER : PROD_AD_UNIT_ID` switch in `BasicBanner.native.tsx` ensures test ads are used in dev builds. Never use real IDs in dev — AdMob treats it as invalid traffic.

---

## 5. Pricing and Ads

CredEasy is free and ad-supported. It has no in-app subscription products, paywall, or free-trial configuration. Configure Google AdMob as described in §4 and declare ads in Play Console.

---

## 6. Google Play Console Setup (🟡 TODO)

1. Pay the one-time $25 fee at <https://play.google.com/console>.
2. **Create app** → name `CredEasy` → default language English → app or game → free.
3. **App content → Privacy policy** — paste the URL from §2.
4. **App content → Ads** — declare "Yes, this app contains ads" (AdMob ads are shown to all users).
5. **App content → Content rating** — fill the questionnaire. Ledger / business app = **Everyone**.
6. **App content → Data safety** — declare what the app collects and shares. See §7 below.
7. **App content → Government apps** — declare "No" unless applicable.
8. **App content → Health apps** — declare "No".
9. **Store presence → Main store listing** — fill in app name, short description, full description, screenshots, feature graphic, icon.
10. **Store presence → Store settings → Pricing** — free, available in all countries.

---

## 7. Data Safety Form (🟡 TODO)

Complete the Data Safety and deletion answers from the shipped build's actual
behavior, backend configuration, and SDK behavior. Audit Google sign-in and
Drive scopes, cloud ledger/profile/media sync, voice audio/transcription,
optional contact access, business photos/QR media, and Google Mobile Ads
identifiers. Distinguish audio sent for transcription from audio retained, and
identify each service provider and purpose. Do not copy a guessed response
table: the app's offline mode, optional permissions, and remote service
configuration affect the answers. Confirm encryption in transit for each
destination and disclose retention/deletion accurately.

---

## 8. Build the Production AAB (🟡 TODO — final step)

EAS Build is the easiest way to produce a signed AAB. Run:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend"
eas login
eas build --profile production --platform android
```

The build runs in the cloud and produces a signed `app-release.aab`. Download it from the EAS dashboard.

For EAS-managed credentials (recommended): when prompted, allow EAS to generate the keystore and store it in your Expo account. Upload the same keystore to Play Console manually after the first build.

For self-managed credentials: generate the keystore per §3, then run `eas credentials --platform android` to upload it.

### 8.1 Local build (alternative)

If you have Android Studio installed and want to build locally:

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend"
npx expo prebuild --clean --platform android
cd android
./gradlew assembleRelease   # or bundleRelease for the AAB
```

The AAB lands in `android/app/build/outputs/bundle/release/app-release.aab`.

---

## 9. Submit to Play Console (🟡 TODO)

1. **Release → Production → Create new release**.
2. Upload the `app-release.aab`.
3. Add release notes (a sentence or two about what's in this version).
4. **Review and roll out** → Start rollout to production.
5. Google reviews the app — first submission typically takes 1–7 days. Updates are faster (a few hours to a day).

---

## 10. Post-Submission

- After the app is live, monitor Play Console → **Reviews and ratings**.
- Watch for crashes in Play Console → **Vitals → Crashes and ANRs**.
- For each new version, bump `version` in `app.json` (the `versionCode` auto-increments via EAS).
- Re-submit privacy policy when the data practices change (sign in, voice, ads, etc.).

---

## Quick Reference

| What | Where |
|---|---|
| App code | `frontend/app/`, `frontend/src/` |
| Backend | `backend/server.py` |
| Privacy policy (template) | `docs/PRIVACY-POLICY.md` |
| SQL migration for cloud | `docs/supabase-migration.sql` |
| EAS project ID | `frontend/app.json` → `extra.eas.projectId` |
| Bundle ID | `frontend/app.json` → `android.package` |
| AdMob app ID (Android) | `frontend/app.json` → `plugins[react-native-google-mobile-ads].androidAppId` |
| Release keystore location | `frontend/android/app/release.keystore` (you generate) |
