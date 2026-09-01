# Build and Install — CredEasy

A practical guide to building the CredEasy app from source and installing it on a physical or emulated Android device. Covers both the local debug workflow and the production submission workflow.

---

## 1. Prerequisites

| Tool | Why | Where to get it |
|---|---|---|
| **Node.js 20+** | Runs Expo CLI, Metro bundler | <https://nodejs.org> |
| **Yarn 1.x or npm** | Package manager | Comes with Node |
| **Java JDK 17** | Required by Android Gradle Plugin 8+ | <https://adoptium.net> |
| **Android Studio** (recommended) | Installs Android SDK, build-tools, platform tools, NDK, and an emulator | <https://developer.android.com/studio> |
| **Expo CLI** | Project-aware commands like `expo run:android` | Installed via `npx` (no global install needed) |
| **An Android device or emulator** | The target for the APK | Physical device with USB debugging, or AVD from Android Studio |

After installing Android Studio, set the environment variable:

- **Windows:** `ANDROID_HOME = C:\Users\<you>\AppData\Local\Android\Sdk`
- **macOS / Linux:** `ANDROID_HOME = $HOME/Library/Android/sdk` (mac) or `$HOME/Android/Sdk` (linux)

Add `$ANDROID_HOME/platform-tools` to your `PATH` so `adb` works from any terminal.

Verify the install:

```bash
adb --version
node --version
java --version
```

---

## 2. Connect a Device

### 2.1 Physical device over USB

1. On the phone: **Settings → About phone**, tap "Build number" 7 times to enable Developer mode.
2. **Settings → Developer options → USB debugging** → turn on.
3. Plug the phone into the computer with a USB cable.
4. On the phone, accept the "Allow USB debugging" prompt.
5. Verify the connection:

   ```bash
   adb devices
   ```

   You should see your device listed with the state `device` (not `unauthorized` or `offline`).

### 2.2 Wireless ADB (what this project uses)

If you see a device like `adb-a8907920-N4Iwhc._adb-tls-connect._tcp`, your phone is connected wirelessly. This requires:

- Phone and computer on the same Wi-Fi network.
- Initial pairing via USB: `adb pair <ip>:<port> <code>` (the code appears on the phone under Developer options → Wireless debugging).
- After pairing, the connection persists until either side restarts.

### 2.3 Emulator

Open Android Studio → **Device Manager** → pick a system image → click the green play button. The emulator appears in `adb devices` as `emulator-5554`.

---

## 3. Local Debug Build (Development)

This is the workflow for testing changes during development. It produces a debug APK that talks to a local Metro bundler, so you can edit JavaScript files and see changes hot-reload on the device.

### 3.1 Install dependencies

```bash
cd "C:/Users/Monodeep Deb/Desktop/CredEasy-Emergent/CredEasy-Emergent-main/frontend"
yarn install
```

### 3.2 Set up environment

Copy the env template into `frontend/.env`. The file is gitignored — never commit it. Required keys:

```
EXPO_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
EXPO_PUBLIC_BACKEND_URL=https://your-backend-host
EXPO_PUBLIC_REVENUECAT_TEST_API_KEY=appl_xxx
EXPO_PUBLIC_REVENUECAT_IOS_API_KEY=appl_xxx
EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY=appl_xxx
```

`EXPO_PUBLIC_*` vars are baked into the JavaScript bundle when the bundler starts. Every time you edit `.env`, restart Metro with `npx expo start -c` (the `-c` clears the cache, otherwise you debug a stale value).

### 3.3 Prebuild native folders (first time only)

Expo generates the `android/` and `ios/` folders from `app.json`. If those folders don't exist yet, or you changed something in `app.json` (added a plugin, changed permissions), run:

```bash
npx expo prebuild --clean --platform android
```

The `--clean` regenerates from scratch. Do NOT hand-edit files in `android/` — they get blown away on the next prebuild.

### 3.4 Build and install

```bash
npx expo run:android
```

What this command does, in order:

1. Builds a debug APK with Gradle (first build: 10–30 minutes; later builds: 1–3 minutes).
2. Installs the APK on the connected device via ADB.
3. Launches the app.
4. Starts Metro bundler in a child process to serve the JavaScript.

The first build downloads Gradle, the Android Gradle Plugin, all the React Native native modules, and compiles them. Later builds reuse the Gradle cache and are fast. To skip the install step (build only, useful for CI):

```bash
npx expo run:android --no-install
```

### 3.5 Use it

After launch:

- The app opens directly to its home screen.
- To view logs: keep the terminal where `expo run:android` is running, or in a separate terminal: `npx react-native log-android`.
- Edit any `.ts` / `.tsx` file in `frontend/app/` or `frontend/src/` — the app reloads automatically.
- Press `r` in the Metro terminal to manually reload.
- Press `j` to open the Chrome DevTools debugger.

### 3.6 Stop Metro and the app

In the Metro terminal: `Ctrl+C` twice. To uninstall from the device: `adb uninstall com.credeasy.app`.

---

## 4. What This Build Does NOT Do

A debug build from `expo run:android`:

- Is **signed with the debug keystore**. The debug key is well-known and ships in the repo; Play Store will reject any APK signed with it. The release build is different — see §5.
- **Connects to Metro at `localhost:8081`**. If you close Metro or take the phone off the same network, the app cannot load JavaScript. For a self-contained install (no Metro), use a release build.
- **Bundles test ad unit IDs** from AdMob (`TestIds.BANNER`). The basic tier shows a Google test banner, not real ads. See `frontend/src/components/ads/BasicBanner.native.tsx`.

---

## 5. Local Release Build (Self-Contained APK)

Useful for QA on a real device without Metro running. Produces an APK with the JS bundle embedded.

```bash
cd frontend
npx expo prebuild --clean --platform android
cd android
./gradlew assembleRelease
```

(Windows: use `gradlew.bat assembleRelease`.)

The APK lands in `android/app/build/outputs/apk/release/app-release.apk`. Install it:

```bash
adb install -r android/app/build/outputs/apk/release/app-release.apk
```

This release is **still signed with the debug key** until you generate a real release keystore (see `docs/PLAY-STORE-SETUP.md` §3). The APK runs without Metro, but cannot be uploaded to Play Store.

---

## 6. Production Build (Cloud)

The cleanest path to a Play-Store-ready AAB is EAS Build. It runs on Expo's cloud infrastructure, handles signing, and produces an `.aab` (Android App Bundle).

### 6.1 One-time setup

```bash
npm install -g eas-cli
eas login
```

If you don't have an Expo account, the `login` command walks you through creating one. It's free.

### 6.2 Generate the release keystore (once)

You need a real keystore to sign production builds. See `docs/PLAY-STORE-SETUP.md` §3 for the full keytool command. Place the file at `frontend/android/app/release.keystore` (already gitignored).

### 6.3 Allow EAS to manage credentials (recommended)

```bash
eas credentials --platform android
```

Follow the prompts. EAS generates and stores a keystore in your Expo account, so you don't have to manage the file yourself. The same keystore is used for every subsequent build.

### 6.4 Build

```bash
cd frontend
eas build --profile production --platform android
```

The build runs in the cloud, takes 5–15 minutes. When done, the dashboard at <https://expo.dev> shows a download link for the signed `app-release.aab`.

### 6.5 Submit (optional)

```bash
eas submit --platform android --latest
```

`eas submit` uploads the AAB to Google Play Console automatically. You still need to fill in the store listing text, screenshots, and Data Safety form by hand in the Play Console before the app is publishable.

---

## 7. ADB Cheat Sheet

| Command | What it does |
|---|---|
| `adb devices` | List connected devices |
| `adb install path/to/app.apk` | Install an APK |
| `adb install -r path/to/app.apk` | Reinstall (keep app data) |
| `adb uninstall com.credeasy.app` | Uninstall |
| `adb shell am start -n com.credeasy.app/.MainActivity` | Launch the app |
| `adb logcat *:E` | Tail error-level logs from the device |
| `adb logcat -s ReactNativeJS:V` | Filter to just JS console.log calls |
| `adb reverse tcp:8081 tcp:8081` | Forward Metro's port (only needed if you launch the app manually, not via `expo run:android`) |
| `adb shell screencap -p /sdcard/screen.png` | Screenshot the device |
| `adb pull /sdcard/screen.png` | Pull that screenshot to your computer |

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `adb: no devices/emulators found` | No device connected, or USB debugging off | Re-check §2.1 |
| `BUILD FAILED` with `SDK location not found` | `ANDROID_HOME` not set | Set the env var, restart terminal |
| `Execution failed for task ':app:mergeDebugResources'` | Old build cache with stale `mipmap-*` icons after a font/icon change | `cd android && ./gradlew clean` then rebuild |
| `Unable to load script. Make sure you're either running Metro...` | App launched but Metro isn't reachable | Run `adb reverse tcp:8081 tcp:8081` and restart the app |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Different signing key on existing install | `adb uninstall com.credeasy.app` then reinstall |
| App crashes on launch with no Metro error | Native module mismatch between JS and native code | `npx expo prebuild --clean` then rebuild |
| `Could not find :app:processDebugManifest` | Old `android/` folder out of sync with `app.json` | `npx expo prebuild --clean` then rebuild |

---

## 9. Where the Outputs Live

| Output | Path |
|---|---|
| Debug APK | `android/app/build/outputs/apk/debug/app-debug.apk` |
| Release APK (local) | `android/app/build/outputs/apk/release/app-release.apk` |
| Release AAB (local) | `android/app/build/outputs/bundle/release/app-release.aab` |
| EAS build artifacts | <https://expo.dev> → your project → Builds |
| Metro logs | The terminal where `expo run:android` is running |
| App crash logs | `adb logcat *:E` or Android Studio → Logcat |

---

## 10. Next Steps After Install

Once the app is on your device:

1. Open it — first run goes through onboarding (business profile setup).
2. Add a test party and a transaction to verify the local ledger works.
3. To test cloud sync, configure `EXPO_PUBLIC_SUPABASE_URL` and `EXPO_PUBLIC_SUPABASE_ANON_KEY` in `frontend/.env` and ensure the Supabase schema in `docs/supabase-migration.sql` has been applied. **Note:** per `CLAUDE.md`, cloud sync is intentionally broken at the architecture level — sign-in is required but data round-trips have known issues. Do not "fix" sign-out data clearing.
4. To test subscriptions, configure RevenueCat env vars and the three product IDs (`basic_monthly`, `adfree_monthly`, `premium_monthly`) in your RevenueCat dashboard.
5. To test the AdMob Basic tier banner, the app must be on a paid tier or trial and `__DEV__` must be false. In dev, you see a Google test banner regardless.
