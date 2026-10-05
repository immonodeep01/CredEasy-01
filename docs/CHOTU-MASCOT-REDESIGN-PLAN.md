# Chotu Ledger Mascot Redesign Plan

## Goal

Replace the Ledger's current quick-actions-menu entry for Chotu with a small,
friendly boy mascot waving from the right side of the screen. Tapping the
mascot opens the existing voice assistant; it does not start listening until
the voice assistant's existing interaction does so.

**Status: Implemented.** The original plan is retained here as design rationale
and validation reference.

## Implemented outcome

- The Ledger now shows Chotu on the right side of a reserved action dock, with
  a direct Add customer action on the left.
- Chotu is an original native-view illustration rather than a third-party
  image or Rive asset. Its separate arm layer rotates briefly when the Ledger
  gains focus, then rests. The app's existing Reanimated dependency drives the
  motion, and reduced-motion users see a still pose.
- The button opens the existing `/voice-assistant` sheet without starting
  microphone capture.
- The dock is hidden while the keyboard or business chooser is visible. It
  reserves layout space rather than covering party rows, and its controls have
  localized labels and 96 dp hit areas.

The implementation uses native view shapes instead of the separately exported
body/arm image layers suggested in the initial asset step. This avoids adding
an image-generation dependency or an unverified external character asset; the
arm remains an independently animated layer.

## Current implementation

- The Ledger is `frontend/app/(tabs)/index.tsx`. Chotu currently appears as an
  action in the lower-right quick-actions menu and routes to
  `/voice-assistant`.
- The voice assistant is `frontend/app/voice-assistant.tsx`.
- `frontend/app/_layout.tsx` already registers the voice assistant as a
  `formSheet` with a 0.92 detent and visible grabber.
- The app uses Expo SDK 54, React Native 0.81, Expo Router 6, and Reanimated 4.
  Rive is not currently a dependency.

## Recommendation

Use a lightweight, original illustration with the existing Reanimated
dependency rather than adding Rive for this single Ledger affordance.

Create a transparent, custom-owned mascot illustration with the body and
raised arm as separate image layers. Anchor the arm layer at the shoulder and
rotate it through a small, gentle wave. The composition remains a compact
right-edge character; the visual artwork may be roughly 64-80 dp tall while
its accessible button hit area is at least 48 by 48 dp. Use an owned/licensed
asset, not a copied character or unverified stock illustration.

Keep the animation restrained: show a brief wave on Ledger entry, then leave
the mascot still. If a continuous loop is preferred after visual testing, keep
it slow and subtle, and disable it when the system requests reduced motion.
This gives the requested waving cue without making a financial ledger screen
visually busy.

### Why not Rive by default?

Rive is a valid alternative if the project wants more expressive, authored
character motion or interactive animation states. Its state machine runtime
supports this category of interaction. However, Rive's React Native package
contains native code and is not compatible with Expo Go; adding it requires a
development/native build and a `.riv` asset pipeline. This project already
ships native builds, so Expo Go compatibility is not a release blocker, but it
would add a dependency and a specialized authoring/export workflow for one
small control.

Use Rive only if the illustration/motion quality cannot be achieved with
separate image layers and Reanimated, and first verify runtime, Expo SDK,
asset-bundling, and build compatibility against the exact package version
selected. The Rive runtime's MIT license does not itself establish rights to
third-party character art or eliminate any editor/export-plan requirements;
confirm both the artwork rights and current export terms for the chosen asset.

## Proposed interaction and placement

1. Remove or replace the current Ledger quick-actions Chotu menu item. Do not
   leave a second, competing Chotu entry point.
2. Place the mascot near the right edge in the lower portion of the Ledger
   content, above the bottom tab bar and outside the scrollable list's primary
   text/tap area.
3. Preserve the existing add-customer action and its current behavior. Rework
   the quick-actions control only as needed so its add-customer affordance
   remains discoverable and does not overlap the mascot.
4. Keep the mascot positioned relative to the Ledger layout and safe-area
   insets, not at a fixed screen coordinate. Check short screens, large text,
   keyboard visibility, and both light and dark themes.
5. Use a single accessible button for the character and its hit target. On
   tap, route to the existing `/voice-assistant` screen; do not duplicate
   assistant state or route logic.
6. Hide or disable the floating mascot while another modal/menu overlays the
   Ledger, when the Ledger is not the visible route, or while the keyboard
   would cover it. Ensure it cannot intercept touches intended for ledger
   rows or the tab bar.

## Accessibility and motion

- Give the button a localized, descriptive label such as “Ask Chotu” and
  “Chotu se baat karein”; use a concise hint such as “Opens the voice
  assistant.” The exact Hindi wording should be reviewed in product context.
- Keep the interactive hit region at least 48 by 48 dp, even if the visible
  character art is smaller. Android recommends a 48 dp touch target; Apple's
  button guidance calls for at least 44 by 44 points. WCAG 2.2 SC 2.5.8 sets
  a 24 by 24 CSS-pixel minimum with stated exceptions. The native platform
  guidance is the more suitable target for this mobile control.
- Ensure TalkBack and VoiceOver announce one meaningful button, not separate
  body/arm image layers. Decorative image layers should not be independently
  focusable.
- Respect the device's reduced-motion setting. Reanimated provides
  `useReducedMotion` and repeat-animation reduced-motion behavior; the reduced
  state should show a still waving pose or a static mascot with no looping
  movement.
- The animation must not imply that Chotu is listening before the user opens
  the assistant. Preserve the existing microphone permission, listening, and
  confirmation behavior.

## Implementation sequence

1. **Design the asset:** produce an original transparent body and arm pair
   aligned at a defined shoulder pivot. Review at intended Ledger scale and
   against the app's light and dark backgrounds. Record asset ownership or
   license.
2. **Replace the Ledger entry point:** integrate a localized accessible
   Pressable in `frontend/app/(tabs)/index.tsx`; keep the add-customer action
   available and remove the redundant Chotu menu action.
3. **Add restrained motion:** use the already-installed Reanimated library to
   rotate the arm layer around its shoulder. Start only on the Ledger, avoid
   unnecessary repeated React renders, and provide a reduced-motion static
   state.
4. **Use the current route:** on press, open `/voice-assistant` using the
   existing route and form-sheet configuration. Do not alter assistant
   behavior or initiate recording from the Ledger.
5. **Tune layout and layering:** account for the safe area, tab bar, Ledger
   content, quick actions, modals, keyboard, small screens, and font scaling.
6. **Validate:** run TypeScript and focused lint; inspect Android and iOS
   layouts; test route opening and dismissal; test light/dark themes and
   reduced motion; verify screen-reader labels, focus order, and touch target;
   confirm the add-customer workflow is unchanged.

## Acceptance criteria

- A small waving-boy mascot is visible at the right side of the Ledger without
  obscuring balances, party rows, quick links, or bottom navigation.
- Tapping it opens the existing Chotu voice-assistant sheet exactly once.
- No microphone capture starts until the user chooses the existing assistant
  interaction.
- The mascot's target remains comfortably tappable and has localized
  screen-reader semantics.
- The animation is subtle, stops or becomes static under reduced motion, and
  does not keep animating after leaving the Ledger.
- The add-customer action remains available and no duplicate Chotu shortcut
  remains in the quick-actions menu.
- TypeScript and focused lint pass; Android and iOS layout and accessibility
  behavior are manually verified.

## Research: sources and findings

### Motion and animation

- [Reanimated `useReducedMotion`](https://docs.swmansion.com/react-native-reanimated/docs/device/useReducedMotion/):
  exposes the system reduced-motion setting so the mascot can select a static
  pose.
- [Reanimated `withRepeat`](https://docs.swmansion.com/react-native-reanimated/docs/animations/withRepeat/):
  supports repeating animations and a reduced-motion behavior. Prefer a short
  entry wave over a perpetual loop for this screen.

### Rive and Expo

- [Rive: Adding Rive to Expo](https://rive.app/docs/runtimes/react-native/adding-rive-to-expo):
  the React Native runtime includes native code and cannot run in Expo Go;
  use a development/native build.
- [Rive: React Native runtime](https://rive.app/docs/runtimes/react-native/react-native):
  documents the React Native runtime and state-machine based playback.
- [Rive: Loading Rive files](https://rive.app/docs/runtimes/react-native/loading-rive-files):
  describes bundling/loading `.riv` files, including Expo asset approaches.
- [Rive runtime licensing](https://rive.app/docs/runtimes/getting-started):
  says official runtimes are MIT-licensed for personal and commercial
  applications. This is runtime licensing; asset ownership and editor/export
  terms must be checked separately.
- [Rive pricing](https://rive.app/pricing/):
  check the current plan's runtime export terms before selecting Rive-authored
  content.

### Navigation

- [Expo Router navigation](https://docs.expo.dev/router/basics/navigation/):
  documents route-based navigation and `router.push`. CredEasy already has the
  target route and presentation configured, so the redesign should reuse it.

### Touch targets

- [Android Developers: Make apps more accessible](https://developer.android.com/guide/topics/ui/accessibility/apps):
  recommends at least a 48 by 48 dp touch target for interactive elements.
- [Apple Human Interface Guidelines: Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons):
  gives a general minimum hit region of 44 by 44 points for buttons.
- [W3C WCAG 2.2: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html):
  defines a 24 by 24 CSS-pixel minimum for pointer targets with exceptions;
  native platform target guidance above is more conservative for this mobile
  control.

## Scope boundary

This redesign changes only the Ledger's Chotu entry-point appearance and
interaction. It does not redesign the voice assistant sheet, change assistant
capabilities, alter ledger operations, or trigger any transaction/inventory
change. All generated ledger/stock changes must continue to require explicit
user confirmation.
