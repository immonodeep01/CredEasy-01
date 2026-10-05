# Chotu Android Home-Screen Widget

The Chotu widget uses `react-native-android-widget@0.22.1` and keeps widget
interaction in the library's headless task handler. It does not use an Activity
for voice capture. A microphone foreground service provides Android's required
user-visible listening notification while the existing `GoogleSpeechCapture`
PCM/VAD path uses the same Google streaming and upload-fallback endpoints as the
in-app assistant. Assistant requests, context shaping, WAV upload transcription,
and MP3 TTS requests are shared with the in-app assistant.

The widget supports conversation, ledger and inventory questions and confirmed
transaction and stock-movement writes. New parties cannot be created from the
widget. Its compact horizontal idle row has one control: the microphone on the
right. While listening, it shows the recognized words and waveform, with Stop
immediately left of Send at the right edge. Speech is submitted only when Send
is tapped; Stop discards it. In result and confirmation states, the only control
is the microphone, except proposed transactions show explicit **Yes** and **No**
buttons; stock changes continue to use spoken yes/no confirmation. All writes
are revalidated against active account/business data before saving. It uses
CredEasy green accents and the saved light/dark theme. The launcher provider is
fixed to a 250dp by 70dp footprint,
approximately four home-screen icons wide and one row high. `NAVIGATE` and
`REMIND` need a visible app/share screen; the widget explains that limitation
and does not launch the app or send a reminder.
On add, resize, and periodic refresh, the headless handler paints a ready view
before loading account/session and saved widget state, so storage or auth
initialization does not leave the launcher's blank placeholder visible.

The package's default headless task timeout is 30 seconds, too short for speech
capture followed by transcription, assistant generation, and TTS. The focused
patch in `frontend/patches/react-native-android-widget+0.22.1.patch` extends it
to two minutes and is applied by the existing `patch-package` postinstall.
Widget component trees must contain only the library's supported widget
primitives; React fragments and ordinary React Native views cannot be rendered
by its headless tree builder.

## Permissions and setup

The Expo config includes the widget library plugin and
`frontend/plugins/with-chotu-widget`. The latter adds microphone foreground
service and notification permissions, service declaration, and native bridge
registration/copying. The widget uses CredEasy's Google speech capture rather
than Android `SpeechRecognizer`.
The package plugin generates the resizable provider, preview image, and
30-minute update behavior. No generated `android/` source needs manual edits.

In CredEasy, open **Settings → Chotu home-screen widget → Enable permissions**
once and grant microphone and notification access. If a permission is later
revoked, the widget shows an explicit setup action; it never requests permission
from the widget itself. Logging in from the widget is also an explicit action.
After login/onboarding, CredEasy returns to Chotu.

## Install and build

From `frontend/`:

```sh
npx expo prebuild --platform android
cd android
.\gradlew.bat app:assembleRelease --console=plain
```

The package dependency is already recorded in `package.json` and both lockfiles.
Do not use `--clean` when preserving existing native project changes. The local
release APK is produced at
`android/app/build/outputs/apk/release/app-release.apk`; local release signing
uses the debug keystore and is for QA only.

For EAS, install dependencies and submit a development or preview build after
prebuild/plugin changes; Expo Go does not include the widget or native bridge.
The app's New Architecture setting and Expo/React Native/Reanimated versions
remain unchanged.

## Manual verification

- Install the development build, long-press the launcher, open **Widgets**, and
  add/rescale Chotu. Verify the preview, light/dark appearance, compact
  horizontal idle row with a right-aligned microphone, and state after
  removing/re-adding it.
- From Settings, grant microphone and notification access. Tap the widget mic
  with CredEasy closed; verify the listening notification, interim transcript,
  Stop and Send controls, and that tapping Send starts processing and spoken TTS.
- Verify Stop discards the transcript without sending it, and silence does not
  submit a command automatically.
- Propose a transaction and verify Yes saves it exactly once while No leaves
  data unchanged; transaction confirmation must not require speaking. Propose
  a stock movement and say “yes” to save or “no” to cancel. Ask to add a party
  and verify the widget directs the user to CredEasy without creating a party
  or asking for phone details.
- Verify `₹46,500`, `46,500 rupees`, and Hindi `₹46,500` are spoken as complete
  number words (“forty six thousand five hundred rupees” / “छियालीस हज़ार पाँच
  सौ रुपये”), not as separate comma groups.
- Test widget mic startup and confirmation when logged out or when the session
  expires. The widget should show **Log in to CredEasy**; only tapping it may
  open login, and successful login should return to Chotu.
- Deny microphone permission initially, deny it permanently, and revoke it
  after setup. Verify the widget directs the user to its setup screen/Android
  Settings without launching automatically. Repeat for notifications on
  Android 13+.
- Disable networking and separately make the voice backend unavailable.
  Confirm the widget surfaces a retryable error and does not claim an action was
  saved. Test unavailable speech recognition, silence, double-tapping the mic,
  stopping mid-listen, and killing the app process.
- Reboot with a widget present and verify its state redraws. Compare widget
  startup and permission behavior on Android 13 and Android 14+.

## Platform notes

The Android widget provider is generated by the library config plugin and its
`ACTION_APPWIDGET_UPDATE` receiver lets Android redraw the widget after reboot.
The microphone service uses Android's documented microphone foreground-service
type and declaration. Android still enforces runtime permission and
while-in-use restrictions; validate widget-triggered service startup on the
target Android 13 and 14+ devices and OEM launchers before release.

The current implementation has not been validated on a physical device or
emulator in this change. In particular, Android-version/OEM foreground-service
behavior, launcher rendering, and spoken TTS require device testing.
