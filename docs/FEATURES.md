# CredEasy — Feature Opportunities

This document is a comprehensive, prioritized list of feature suggestions for CredEasy — a mobile-first business ledger (khata) app for Indian shopkeepers, built with React Native/Expo + Flask backend + Supabase.

The goal is to identify realistic feature opportunities that enhance functionality, user experience, scalability, or performance without requiring major architectural changes (e.g., a cloud sync rewrite is explicitly out of scope — see `FIXING-GUIDE.md` for that workstream).

## Methodology

The first section ("Codebase-Informed Features") was derived from a hands-on audit of the existing code. The second section ("Competitor-Informed Features") was derived from research into competing products (OkCredit, Khatabook, Vyapar, TallyPrime, Udhari Book, VoiceKhata, AiXpense, BizBeat, Hisaabo, myBillBook, Spendrix, FinArt, Trakio, Axio, and others).

Features are ranked across three tiers:
- **Tier 1**: High value, low complexity — implement first
- **Tier 2**: Medium value, medium complexity — second wave
- **Tier 3**: Higher complexity or niche value — third wave
- **Tier 4 (Deferred)**: Architectural work explicitly outside current scope

Each feature includes: a description, value proposition, integration approach (concrete file/pattern references), complexity assessment, and rationale for inclusion.

---

## Status of Features in This Document (Audit: 2026-09-03)

Re-audit of the codebase confirmed several items from the original list are **already shipped** or have stronger implementations than the doc suggested. Cross-referenced against `frontend/app/*` and `backend/server.py`:

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Party Deletion | **Partially done** — `StorageService.deleteParty()` exists, used in tests, but no UI button. Still valid. | `storage-service.ts:133` |
| 2 | Voice Action Dispatch | **Done** — full `runActions()` loop with ADD_TRANSACTION / ADD_PARTY / multi-step add-party state machine, contact search, opening balance flow, REMIND, NAVIGATE. | `voice-assistant.tsx:382-545` |
| 3 | Bill History / View Saved Bills | **Not done** — bills are saved but no history UI. Still valid. | `billing.tsx` |
| 4 | Export to CSV/Excel | **Not done** — only PDF export. Still valid. | `reports.tsx:62-103` |
| 5 | Transaction Search in Party Detail | **Not done** — search exists on dashboard/parties but not party-detail. Still valid. | `party-detail.tsx` |
| 6 | WhatsApp Share for Party Balance | **Done** — `handleWhatsAppReminder()` opens `whatsapp://send?phone=91...` with balance message. | `party-detail.tsx:103-114` |
| 7 | Smart Reminders (REMIND action) | **Done** — voice `REMIND` action wired to WhatsApp. Dashboard "Top 5" widget is the remaining piece. | `voice-assistant.tsx:523-530` |
| 8 | Invoice Numbering | **Not done** — bills use random `newId('bill')`. Still valid. | `mock.ts:Bill` |
| 9 | Multi-Currency | **Not done** — `formatMoney()` INR-only. Still valid. | `utils/ledger.ts` |
| 10 | Hindi Number Input (Words-to-Digits) | **Not done** — backend already does this for voice. Still valid for typed input. | `add-transaction.tsx` |
| 11 | JSON Backup/Restore | **Not done** — critical given cloud sync is broken. Still valid. | `storage-service.ts` |
| 12 | Dark Mode | **Not done** — token system in place, just not exposed. Still valid. | `utils/colors.ts` |
| 13 | Transaction Categories | **Not done**. Still valid. | `mock.ts:Transaction` |
| 14 | Transaction Editing | **Not done**. Still valid. | `add-transaction.tsx` |
| 15 | Local Notification Reminders | **Not done** — `expo-notifications` not in deps. Still valid. | `package.json` |
| 16 | Customer Photo / Avatar | **Not done** — `photoUri?` field exists in `Party` type but no UI. Still valid. | `mock.ts:Party`, `add-party.tsx` |
| 17 | Recurring Transactions | **Not done**. Still valid. | — |
| 18 | Inventory Tracking | **Not done**. Still valid (large scope). | — |
| 19 | Cloud Sync Repair | **Deferred** — still out of scope. | `FIXING-GUIDE.md` |
| 20 | Aging Report | **Not done**. Still valid. | `utils/ledger.ts`, `reports.tsx` |
| 21 | SMS Auto-Parsing | **Not done**. Still valid (privacy-sensitive). | — |

### Bonus capabilities discovered in the codebase (not on the original list)

These shipped but were never added to FEATURES.md — captured for completeness:

- **PDF/DOCX Ledger Import** — `POST /api/import/parse` extracts parties/transactions from uploaded documents, reviewed before commit. Differentiator vs OkCredit/Khatabook which don't offer this.
- **PDF Statement Export per Party** — Premium-gated, `partyStatementHtml()` generates formatted PDF for a single party.
- **Edge TTS Voice Replies** — Voice assistant speaks back in Hindi (`hi-IN-SwaraNeural`) or English (`en-US-JennyNeural`); `gpt-4o-mini-tts` as fallback.
- **App PIN + Biometric Lock** — `AppLockScreen` + `expo-secure-store` with AsyncStorage fallback.
- **Google Sign-In (Supabase OAuth)** — Profile avatar, name, email displayed in Settings.
- **Receipt/Bill photo attachment on transactions** — `Transaction.photoUri?` field exists in `mock.ts:25` but no UI.
- **GST Toggle (18%) on Bills** — Subtotal/GST/grand total breakdown in `billing.tsx`.
- **Two sign-out paths** — "Keep data on phone" vs "Back up and remove" — both gated by cloud-push success.
- **Account deletion** — Hits Supabase admin API to delete the auth user.

---

## Tier 1 — High Value, Low Complexity

These leverage existing infrastructure and require minimal new code.

### 1. Party Deletion

- **Description:** Add a "Delete Party" button in `party-detail.tsx` with PIN confirmation.
- **Value Proposition:** Users need to remove parties (typos, duplicate entries, archived contacts). Currently impossible — `StorageService.deleteParty()` exists but has no UI. Every ledger app allows contact removal.
- **Integration:** Reuse the existing `SecurityPinModal` component (already handles verify/set/confirm from the transaction-delete feature). Add `Alert.alert` with destructive action in `party-detail.tsx`, mirroring the transaction delete pattern already built. Add a trash icon to the top-right of the party detail header.
- **Complexity:** Low — single screen, ~15 lines of code.
- **Rationale:** Storage layer already has `deleteParty(partyId)`. Auth gate (`SecurityPinModal`) is battle-tested. Competitor parity: OkCredit and Khatabook both offer party deletion.

### 2. Voice Assistant → Transaction Execution (Frontend Action Dispatch)

- **Description:** Connect the `actions` array returned by `/voice/assist` to actual storage writes in `voice-assistant.tsx`.
- **Value Proposition:** The voice assistant currently returns `ADD_TRANSACTION` and `ADD_PARTY` actions with sanitized amounts and party names, but the frontend only speaks the `reply` field back to the user — it never writes to the ledger. The user says "Ramesh ko 500 diye" and the assistant talks back but the ledger isn't updated. This is the single biggest gap between the app's headline feature and its actual behavior. The backend already does the hard work (LLM intent parsing, action sanitization, multi-step ADD_PARTY state machine).
- **Integration:** In `voice-assistant.tsx`, after parsing the JSON response, iterate over `actions` and dispatch to:
  - `StorageService.addTransaction()` for `ADD_TRANSACTION`
  - `StorageService.addParty()` for `ADD_PARTY` / `ADD_PARTY_COMPLETE`
  - `router.push('/add-party?...')` for `ASK_PARTY_SPELLING` (begin add-party flow)
  - Show a toast/snackbar confirming each action with the party name + amount
  - Maintain a `multiStep` state to track ADD_PARTY progress across turns
- **Complexity:** Low–Medium — action dispatch loop, multi-step state tracking, ~50–80 lines.
- **Rationale:** Backend `sanitize_actions()` already validates all fields (amount, type, party name). Frontend just needs to wire up the write path. The LLM's multi-step ADD_PARTY flow (`ASK_PARTY_SPELLING` → `SELECT_CONTACT` → `ASK_OPENING_BALANCE` → `ADD_PARTY_COMPLETE`) is also defined in the system prompt and needs a frontend state machine to track progress. VoiceKhata, BookKeepa, and JustPaid.io all demonstrate that voice-to-transaction is the killer feature for shopkeeper apps.

### 3. Bill History / View Saved Bills

- **Description:** Add a "Bill History" section in `billing.tsx` that lists previously generated bills, with view/share actions.
- **Value Proposition:** Users generate bills but have no way to view, reprint, or share past bills. OkCredit, Vyapar, and myBillBook all show a bill history. The `Bill` data structure already exists; the UI just doesn't display it.
- **Integration:** Add a collapsible `FlatList` section in `billing.tsx` (below the create form) or a dedicated sub-screen accessible from a history tab. Fetch from `StorageService.getBills()`, group by date, show party name + total + status (UNPAID/PAID). Add "View" (re-render to PDF) and "Share" actions. Add a "Mark Paid" button that converts the UNPAID bill to a paid transaction in the ledger.
- **Complexity:** Low — same component structure as the existing items list, ~40 lines for the list, ~20 more for the detail/re-share.
- **Rationale:** `StorageService.addBill()` already persists complete bill objects. The data is sitting in AsyncStorage unused. Competitor parity is table stakes.

### 4. Export to CSV/Excel

- **Description:** Add CSV export alongside the existing PDF export in `reports.tsx`.
- **Value Proposition:** Accountants and small businesses strongly prefer CSV/Excel for data entry. PDF is read-only; CSV is editable and importable into Tally, Vyapar, and accounting software. OkCredit, Vyapar, TallyPrime, Hisaabo, and Acclo IQ all offer CSV/Excel export. Most charge for full Excel export — offering it free differentiates CredEasy.
- **Integration:** Add a new export button in `reports.tsx` next to the PDF button. Use a simple string builder (no library needed — CSV is just comma-separated values with quoted strings, with `\r\n` line endings). Format: `Date, Party, Type, Amount, Note`. Trigger `Sharing.shareAsync()` with the CSV file written to cache via `FileSystem.writeAsStringAsync()`. Escape commas/quotes/newlines in fields properly.
- **Complexity:** Low — no new dependencies, ~30 lines.
- **Rationale:** `generateAndSharePdf` already handles file writing and sharing. CSV generation is simpler. This is a direct complement to the existing PDF feature and a free differentiator vs. competitors that gate CSV behind paywalls.

### 5. Transaction Search in Party Detail

- **Description:** Add a `TextInput` search field in `party-detail.tsx` that filters the transaction list by note text or amount.
- **Value Proposition:** As a party's transaction history grows (50+ entries), scrolling becomes painful. A search field is the most basic expected feature for any list view. The dashboard and parties list already have search; party detail is the odd one out.
- **Integration:** Add `TextInput` above the transactions `FlatList` in `party-detail.tsx`. Add `filteredTxs = useMemo(...)` that filters by note substring or amount string match. Use the existing `Ionicons search` icon pattern from dashboard and parties screen.
- **Complexity:** Low — add `TextInput` + `filteredTxs` useMemo, ~15 lines.
- **Rationale:** Three other screens already implement the same search bar pattern. Bringing the fourth screen to parity is a 15-minute task.

### 6. WhatsApp Share for Party Balance

- **Description:** Add a "Share via WhatsApp" button on `party-detail.tsx` that sends a formatted balance statement.
- **Value Proposition:** WhatsApp is the primary communication channel for Indian small businesses. Khatabook, OkCredit, and VoiceKhata all promote WhatsApp sharing as a headline feature. Sending a party's balance summary with one tap is a natural workflow ("Ramesh bhai ka hisaab: ₹5,000 baaki").
- **Integration:**
  ```typescript
  const message = `${party.name} ka khata\n${lang === 'hi' ? 'कुल बकाया' : 'Total'}: ${formatMoney(balance)}\n\n${lang === 'hi' ? 'CredEasy से बनाया' : 'Made with CredEasy'}`;
  const whatsappUrl = `whatsapp://send?phone=91${party.phone}&text=${encodeURIComponent(message)}`;
  Linking.openURL(whatsappUrl).catch(() => Alert.alert('WhatsApp not installed'));
  ```
- **Complexity:** Low — ~15 lines in `party-detail.tsx`.
- **Rationale:** `Linking.openURL` pattern is already used for SMS (in `add-transaction.tsx`) and PDF (`Linking.openURL` for Android system viewer). WhatsApp uses the same URL scheme. Khatabook's #1 growth channel is WhatsApp shares; the same viral mechanic applies here.

---

## Tier 2 — Medium Complexity, Medium Value

These require more work but unlock meaningful functionality.

### 7. Smart Reminders / Payment Due Notifications

- **Description:** Wire up the existing `REMIND` voice action + add a "Top 5 Balances" widget on the dashboard that highlights parties needing follow-up.
- **Value Proposition:** Shopkeepers forget to follow up. A WhatsApp-style reminder ("Ramesh ka ₹5,000 baaki hai — kab dega?") drives collections. Khatabook, OkCredit, myBillBook, FinArt, BizBeat, and Trakio all offer reminder workflows; several monetize them via premium tier. The backend already has a `REMIND` action type in the voice assistant system prompt — it's just not wired up.
- **Integration:**
  1. **Backend:** Extend `/voice/assist` so the `REMIND` action can include a custom message ("Ramesh ko remind karo ki 5000 baaki hai").
  2. **Frontend:** When `REMIND` action received, show an alert offering to share via WhatsApp/SMS with pre-filled message (`Linking.openURL('whatsapp://send?text=...')`).
  3. **Dashboard widget:** Add a "Pending Collections" card on the dashboard showing the top 5 parties by positive balance with a "Remind" button on each. Use the existing `aggregateTotals` + sort.
- **Complexity:** Medium — reminder action wiring (~30 lines), dashboard widget (~30 lines).
- **Rationale:** The `REMIND` action is already defined in the system prompt. The SMS/WhatsApp intents already exist in other screens. Only the action dispatch and widget are missing. Khatabook's "free WhatsApp reminder" was their #1 differentiator vs OkCredit when it launched.

### 8. Invoice Numbering / Sequential Bill IDs

- **Description:** Add auto-incrementing invoice numbers to bills (e.g., `INV-001`, `INV-002`).
- **Value Proposition:** GST-compliant businesses need sequential invoice numbering. Currently bills have random `newId('bill')` strings like `bill-1740...-a1b2c3d4`. Accountants and tax filing require a readable, sequential format. Vyapar, TallyPrime, and myBillBook all enforce sequential numbering. It's a legal requirement in many Indian states for GST-registered businesses.
- **Integration:** Store a `lastInvoiceNumber` counter in AsyncStorage (`@credeasy_invoice_num`). Increment on each bill creation. Format configurable (prefix + zero-padded number, e.g., `INV-2026-0001`). Add `number: string` field to `Bill` type in `mock.ts`. Display in `billing.tsx` form before save and on the bill detail.
- **Complexity:** Low–Medium — new storage key, update `addBill()`, update bill display, migration for existing bills.
- **Rationale:** The `Bill` type already has an `id` field. A `number` field is a minimal schema change. This unlocks GST compliance and accounting integration.

### 9. Multi-Currency Display

- **Description:** Allow display of balances in ₹ (default) with toggle for approximate USD/EUR/GBP conversion.
- **Value Proposition:** Some shopkeepers deal with international suppliers (import businesses, e-commerce resellers) or want to show balances to overseas family members. Voice Accountant App, Spendrix, and BookKeepa all offer multi-currency display. This is a "nice to have" that competitors charge for.
- **Integration:** Add a currency selector in Settings (₹ INR, $ USD, € EUR, £ GBP). Use a hardcoded/fallback exchange rate table (no API needed for v1 — just display conversion with a "Rates may vary" disclaimer). Extend `formatMoney()` to accept a `currency` parameter. Pass currency through context or directly.
- **Complexity:** Low — add to settings state, pass currency through to `formatMoney()`.
- **Rationale:** `formatMoney()` already exists as a central helper in `src/utils/ledger.ts`. One parameter addition propagates across all displays.

### 10. Hindi Number Input (Words-to-Digits)

- **Description:** Allow typing amounts in Hindi words in the transaction input field.
- **Value Proposition:** Shopkeepers may not be comfortable with numerals. Accepting "paanch sau" → 500 or "do hazaar" → 2000 lowers the barrier to digital entry. AiXpense, VoiceKhata, and Trakio all support Hindi/Hinglish number input. This complements the existing voice assistant.
- **Integration:** Add a utility `hindiWordsToNumber()` in `src/utils/ledger.ts` (simple map: सौ/सो=100, हज़ार/हजार=1000, लाख/लाख=100000, etc., with both Devanagari and Romanized variants). Apply in `add-transaction.tsx` before `toPositiveMoney()`. Show hint text in Hindi below the amount field. Use a debounce so it doesn't fight the user's typing.
- **Complexity:** Low — ~30-line utility function, integration in one screen.
- **Rationale:** The voice assistant already converts Hindi number words server-side. This brings the same capability to typed input. Helpful for the "1.5 lakh" / "दो हजार" typing style common in Indian commerce.

### 11. JSON Backup/Restore

- **Description:** Export all ledger data as a single JSON file; re-import to restore or migrate to a new device.
- **Value Proposition:** With cloud sync deliberately broken (per CLAUDE.md), a local JSON backup is the only recovery path. Users upgrading phones need a way to transfer data. Hisaabo exports `.tar.gz` archives, Acclo IQ exports `.json.gz`, Sahab Budget exports JSON — all are standard for this category.
- **Integration:** Add `exportAllData()` and `importAllData()` to `storage-service.ts`. Export: serialize all AsyncStorage keys (parties, transactions, bills, profile, language, PIN hashes, trial date) to a single JSON object, write via `FileSystem`. Import: parse JSON, validate schema, write back to AsyncStorage keys. Add buttons in Settings under "Data Management." Add confirmation modal that warns "Importing will replace all current data" with a PIN gate.
- **Complexity:** Medium — file I/O, validation, conflict handling (~100 lines).
- **Rationale:** Storage keys are already named and structured (`@hisab_parties_v1`, etc.). The import is the inverse of the export. The PIN gate reuses existing `SecurityPinModal`. This is critical given that cloud sync is broken.

### 12. Dark Mode

- **Description:** Add a dark theme option using the existing `colors.ts` token system.
- **Value Proposition:** Users in low-light environments (evening shop, nighttime use) prefer dark mode. Standard expectation in 2024 mobile apps. Spendrix explicitly markets dark mode; Axio, Trakio, and most modern competitors have it. Battery savings on AMOLED are a bonus.
- **Integration:** Extend `colors.ts` with a `darkColors` namespace (same token names, different values). Add a `ThemeContext` in `_layout.tsx` that toggles between light/dark palettes. Pass theme via context. Screens reference `colors.background`, `colors.surface`, etc. which already exist as named tokens — so dark mode is a token-swap, not a component rewrite. Add toggle in Settings.
- **Complexity:** Medium — token file doubles in size, context provider, Settings toggle, persistence.
- **Rationale:** `colors.ts` already uses named tokens rather than hardcoded values (see the OkCredit-style palette work in the handoff log). Dark mode is one of the easier UX wins because the token system is already in place.

---

## Tier 3 — Higher Complexity, Niche Value

Valuable but require more investment or architectural decisions.

### 13. Transaction Categories / Tags

- **Description:** Add optional categories (Groceries, Clothing, Medicine, Rent, Utilities, etc.) to transactions and parties.
- **Value Proposition:** Business owners want to see "how much did I sell in Groceries this month?" for tax filing or inventory planning. Currently all transactions are flat. Vyapar, BizBeat, and FinArt all offer category breakdowns.
- **Integration:** Add `category?: string` to `Transaction` type in `src/mock.ts`. Add a category picker (chips) in `add-transaction.tsx`. Add category filter in `reports.tsx`. Group totals by category. Show a pie chart in reports.
- **Complexity:** Medium — type changes, UI updates across 3 screens, aggregation in reports, optional chart.
- **Rationale:** `aggregateTotals()` in `ledger.ts` is extensible. Adding category grouping follows the same pattern as the existing supplier/customer split. BizBeat's "AI Smart Insights" use this categorization as their headline feature.

### 14. Transaction Editing

- **Description:** Allow editing an existing transaction's amount, type, or note.
- **Value Proposition:** Currently transactions can be deleted but not modified. This is a common gap — users make typos and need to correct them. Vyapar, OkCredit, Khatabook, and TallyPrime all offer edit-in-place.
- **Integration:** Add an "Edit" button per transaction in `party-detail.tsx` (tap to open action sheet with Edit/Delete). Opens the `add-transaction.tsx` flow pre-filled. Store the original transaction ID, update instead of creating new. Add `StorageService.updateTransaction(id, partial)`.
- **Complexity:** Medium — `StorageService.updateTransaction()`, edit flow UI, confirmation modal, audit log optional.
- **Rationale:** `add-transaction.tsx` already handles the form. Prefilling it and switching from "add" to "edit" mode is a small modification. Useful when shopkeepers mistype amounts — without edit, they have to delete and re-add (which loses original timestamp).

### 15. Local Notification Reminders (Scheduled)

- **Description:** Schedule a local notification to remind the user about a party's balance at a specific date.
- **Value Proposition:** "Remind me to follow up with Ramesh next week" — this bridges the app to the shopkeeper's calendar without needing cloud sync. FinArt, PaisaTrack, BizBeat, Trakio, and myBillBook all offer scheduled reminders.
- **Integration:** Use `expo-notifications` (Expo provides it natively). Add a "Schedule Reminder" button in `party-detail.tsx` (date picker + time picker). Store scheduled reminders in AsyncStorage. Show notification with party name and balance amount at the scheduled time. Handle permission flow gracefully.
- **Complexity:** Medium — notification permission flow, reminder storage, notification scheduling, deep-link from notification to party detail.
- **Rationale:** Local notifications don't require cloud sync. This is a pure client-side feature. Adds an engagement loop without backend work.

### 16. Customer Photo / Avatar Upload

- **Description:** Allow users to attach a photo to a party (taken with camera or picked from gallery).
- **Value Proposition:** Shopkeepers with many similar-looking customers (multiple "Ramesh" entries, common Indian names) often confuse parties. A photo helps disambiguate. Khatabook, OkCredit, and most modern CRM apps support this. Useful for the shopkeeper who has 50+ customers.
- **Integration:** Add `photoUri?: string` to `Party` type. Use `expo-image-picker` (already added for QR codes per handoff log). Add camera/gallery buttons in `add-party.tsx`. Display thumbnail in `party-detail.tsx` and party list rows (replacing or alongside the letter avatar).
- **Complexity:** Medium — image picker integration, storage URI management, display component, list rendering performance for many photos.
- **Rationale:** `expo-image-picker` is already a dependency (used for business QR codes). Storage keys are just URIs. No backend changes needed.

### 17. Recurring Transactions / Standing Orders

- **Description:** Set up a transaction that auto-creates on a schedule (monthly rent from a supplier, weekly milk delivery credit, etc.).
- **Value Proposition:** Many shopkeeper transactions are repetitive (weekly supplier deliveries, monthly rent). Auto-creating recurring entries saves time. BizBeat, AiXpense, Spendrix, PaisaTrack, and Trakio all offer recurring transactions.
- **Integration:** Add a `RecurringTransaction` type and storage. New screen to set up recurrence (amount, party, type, frequency: daily/weekly/monthly). On app launch, check for due recurrences and prompt user to confirm before creating. Add a "Skip this one" option.
- **Complexity:** Medium–High — new data model, scheduler logic, UI for management, edge cases (what if the party was deleted, what if the amount changes, what about history).
- **Rationale:** This adds significant value for shopkeepers with stable supplier/customer relationships. Would need careful UX to avoid surprise auto-entries.

### 18. Inventory Tracking (Simple Stock)

- **Description:** Add basic inventory tracking — items with current stock, low-stock alerts, deduct-on-bill.
- **Value Proposition:** Vyapar, myBillBook, and TallyPrime are the heavy hitters in this space. OkCredit and Khatabook have started adding lightweight inventory. Shopkeepers who also do billing (`billing.tsx` already exists) frequently want stock counts.
- **Integration:** Add `Item` type with `currentStock`, `lowStockThreshold`, `unit`. Add `inventory` storage. When a bill is generated with line items, decrement stock. Add low-stock alert in dashboard. Add an Inventory tab.
- **Complexity:** High — new data model, integration with billing, UI for stock management, multiple screens.
- **Rationale:** Bigger scope than the other features. The data model is independent of the ledger (stock is its own domain). Vyapar proves this is a paid feature in the segment; offering a lightweight version for free is a real differentiator.

---

## Tier 4 — Deferred (Architectural Work)

Explicitly out of scope for incremental features. Per CLAUDE.md, cloud sync is deliberately broken and the UUID/schema/auth migration is the larger workstream tracked in `docs/FIXING-GUIDE.md`.

### 19. Cloud Sync Repair

- **Description:** Fix Supabase sync so data persists to the cloud.
- **Value Proposition:** Multi-device access, real backup, the app's core promise. Currently all upserts fail silently. Khatabook, OkCredit, and Hisaabo all offer cloud sync as a baseline expectation.
- **Integration:** Per `docs/FIXING-GUIDE.md`:
  1. Migrate party/transaction IDs from string format to UUID
  2. Fix RLS policies (add `WITH CHECK` clauses)
  3. Fix the auth token mismatch (Supabase JWT vs `st_...` session tokens)
  4. Fix `pushToCloud` / `pullFromCloud` in `src/lib/supabase.ts`
- **Complexity:** High — schema migration, RLS policy fixes, auth flow overhaul, testing.
- **Rationale:** This is the elephant in the room. Everything else on this list is incremental improvement; this is the architectural fix that enables true multi-device, multi-user, and real backup. Listed here for completeness only.

### 20. Aging Report (30/60/90 Days Outstanding)

- **Description:** Show balances bucketed by age of oldest unpaid transaction.
- **Value Proposition:** TallyPrime's aging report is its #1 enterprise feature. A 30/60/90-day aging breakdown helps shopkeepers prioritize collections. Vyapar and Hisaabo offer this.
- **Integration:** Add `partyAging(party, txs, buckets)` to `ledger.ts` (groups by days since oldest DEBIT without subsequent CREDIT). Add an "Aging" card in `reports.tsx` with three rows: 0-30 days, 31-60 days, 60+ days, showing total outstanding per bucket.
- **Complexity:** Medium — ledger math extension, new report section, requires all transactions to be loaded (already are in reports).
- **Rationale:** Pairs naturally with the Reminders feature (#7). Aging + reminders is a complete collections workflow.

### 21. SMS Auto-Parsing (Bank SMS → Transaction)

- **Description:** Auto-detect bank transaction SMS (UPI, card, IMPS) and prompt to add as a transaction.
- **Value Proposition:** Axio and Trakio built their entire user base on this. Reads the user's bank SMS, detects payment events, prompts to add. Massive time saver for shopkeepers who receive dozens of UPI payments daily.
- **Integration:** Use Android's SMS read permission (already requested in some flows per the handoff log — verify). Parse incoming SMS for UPI patterns (`Rs.`, `INR`, `debited`, `credited`, `to VPA`, etc.). Show a heads-up notification "Add this ₹500 payment from Ramesh?" with confirm/dismiss.
- **Complexity:** High — requires Android SMS permission (privacy-sensitive), regex patterns vary by bank, iOS doesn't allow SMS reading, need user education.
- **Rationale:** Privacy-sensitive feature. Axio got dragged into controversies over SMS reading. Should be opt-in with clear consent. Could be a premium feature.

---

## Cross-Cutting Observations (From Competitor Research)

Patterns that appear in nearly every competitor and would benefit CredEasy:

| Pattern | OkCredit | Khatabook | Vyapar | TallyPrime | Hisaabo | myBillBook | BizBeat | VoiceKhata | Trakio | Spendrix |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| WhatsApp share | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | — | — |
| CSV export | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Multi-language | ✓ 12+ | ✓ 12 | ✓ 5+ | ✓ 5+ | ✓ | ✓ | ✓ | ✓ 12 | ✓ | ✓ 10+ |
| Dark mode | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | ✓ |
| Reminders | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Cloud backup | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | Google Drive |
| Recurring tx | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Voice input | — | — | — | — | — | — | — | ✓ | — | — |
| Aging report | — | — | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| Multi-currency | — | — | ✓ | ✓ | — | — | — | — | — | ✓ 20+ |
| Bank SMS parse | — | — | — | — | — | — | — | — | ✓ | — |
| Inventory | ✓ lite | ✓ lite | ✓ full | ✓ | ✓ | ✓ | — | — | — | — |
| Customer photo | ✓ | ✓ | ✓ | — | ✓ | ✓ | — | — | — | — |
| Local backup (JSON) | — | — | ✓ | ✓ | ✓ | ✓ | — | — | — | ✓ |
| Sequential invoice # | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Free WhatsApp reminder | ✓ | ✓ | — | — | — | — | — | — | — | — |
| Loans/credit products | ✓ | — | — | — | — | — | — | — | — | — |
| POS / barcode | — | — | ✓ | — | — | ✓ | — | — | — | — |

**What's table-stakes for the segment (must-haves to compete):**
- WhatsApp share (#6)
- CSV export (#4)
- Reminders (#7)
- Party deletion (#1)
- Bill history (#3)
- Local JSON backup (#11) — critical given cloud sync is broken

**What's a CredEasy differentiator (most competitors don't have these):**
- Voice assistant in Hindi/English/Hinglish (already built but needs action dispatch — #2)
- PDF/DOCX ledger import (already built per handoff log)
- No-login trial experience (already in place via trial start)

**What's a premium upsell opportunity:**
- Multi-currency (#9)
- Dark mode (#12) — or could be free to compete
- Aging report (#20)
- SMS auto-parsing (#21)

---

## Prioritization Recommendation

**Implement first (next 2–3 sessions):**
1. Party Deletion (#1) — 15 min
2. Transaction Search in Party Detail (#5) — 15 min
3. WhatsApp Share for Party Balance (#6) — 30 min
4. Voice Action Dispatch (#2) — 2 hours
5. Bill History (#3) — 1 hour

**Implement second (next 2 weeks):**
6. CSV Export (#4)
7. Reminders / Top 5 Balances widget (#7)
8. Invoice Numbering (#8)
9. Hindi Number Input (#10)
10. JSON Backup/Restore (#11)

**Decide based on user feedback:**
- Dark mode (#12) — very high demand, medium effort
- Transaction categories (#13) — depends on whether users ask for reporting depth
- Transaction editing (#14) — table stakes, defer until post-cloud-sync

**Hold for after cloud sync is fixed (#19):**
- Aging report (#20)
- Recurring transactions (#17)
- SMS auto-parsing (#21) — privacy-sensitive
- Inventory tracking (#18) — biggest scope

---

## Sources

- [OkCredit](https://okcredit.in/) — business ledger with WhatsApp reminders, loans, multi-language
- [Khatabook](https://khatabook.com/) — bahi-khata digital, 4+ crore businesses
- [Vyapar](https://vyapar.com/) — GST invoicing + inventory
- [TallyPrime](https://tallysolutions.com/tally-prime/) — formal accounting + audit
- [Hisaabo](https://hisaabo.in/) — invoice + backup
- [VoiceKhata](https://voicekhata.com/) — voice-first ledger
- [AiXpense](https://aixpense.in/) — voice expense tracker, 22 languages
- [BizBeat](https://bizbeat.in/) — AI insights + recurring expenses
- [Trakio](https://trakio.co.in/) — SMS auto-parsing
- [myBillBook](https://mybillbook.in/) — MSME bookkeeping with reminders
- [Spendrix](https://spendrix.in/) — multi-currency, dark mode
- [FinArt](https://finart.app/) — SMS-based budget tracking
- [BookKeepa](https://bookkeepa.com/) — conversational finance
- [JustPaid.io](https://www.prnewswire.com/) — voice financial co-pilot
- [Forbidden Finance](https://403fin.io/) — CSV/JSON export patterns
- [Acclo IQ](https://accloiq.com/) — JSON.gz backup/restore

---

---

## New Gaps From Competitor Research (September 2026 refresh)

Fresh research against the current generation of competitors surfaced several features **not covered in the existing list**. These are 2025-2026 table-stakes features that ship in newer apps and that CredEasy is missing.

### N1. Auto Interest Calculation on Credit Balances — `AUTO_INTEREST` (HIGH VALUE)

- **Description:** Apply a configurable interest rate (daily/monthly compounding) to outstanding party balances and surface accrued interest in the ledger, dashboard, and PDF exports.
- **Competitor:** Aukra explicitly markets this as "FIRST IN INDIA" and a headline differentiator. Khatabook's `simple-interest` calculator, `EMI calculator`, and `business-loan-EMI calculator` are now in-app too.
- **Value Proposition:** Shopkeepers regularly extend 30–90 day credit. Interest accrual is real money they're losing or leaving unclaimed. For supplier relationships (where the shop owes money), interest is also a fair-warning signal.
- **Integration:**
  - New `InterestConfig` type: `rate: number` (annual %), `compounding: 'daily' | 'monthly'`, `appliesTo: 'receivables' | 'payables' | 'both'`.
  - Stored in AsyncStorage; per-party override supported.
  - Add `computeAccruedInterest(party, txs, config, asOf)` to `src/utils/ledger.ts`.
  - Display "₹X interest accrued" line in `party-detail.tsx` running balance view.
  - Add to dashboard "Top 5 Overdue" widget.
- **Complexity:** Medium — needs config UI, ledger math extension, PDF export update, opt-in default (off).
- **Why Now:** Aukra launched this in 2026 and it's getting press. CredEasy is the natural home for it because the voice assistant already understands the shopkeeper workflow.

### N2. UPI Deep-Link Payment Collection from Party Balance — `PAY_VIA_UPI` (HIGH VALUE)

- **Description:** A "Collect via UPI" button on `party-detail.tsx` and on each UNPAID bill that opens the customer's UPI app with a pre-filled `upi://pay?pa=...&am=...&tn=...` deep link.
- **Competitor:** Razorpay UPI QR, Aukra, Vyapar, myBillBook, EnKash — all generate dynamic UPI payment links / QR codes for each invoice. This is now table-stakes for any Indian SMB app.
- **Value Proposition:** Today, the WhatsApp reminder message inlines the UPI ID and the customer has to retype it. A single tap to open GPay/PhonePe/Paytm with the exact amount and a remark like "Payment for INV-23" closes the loop in 3 seconds.
- **Integration:**
  - Use `Linking.openURL(\`upi://pay?pa=${profile.upiId}&am=${amount}&tn=${encodeURIComponent('CredEasy ' + partyName)}&cu=INR\`)` (works on Android; iOS has different handlers).
  - Add `Ionicons card` button on the balance banner next to "Remind".
  - On each UNPAID bill row, add a "Collect" button that builds the same link with the bill number in the remark.
  - Optional: also generate a one-time QR code using a small QR library (or `react-native-qrcode-svg`) for the print-on-bill use case.
- **Complexity:** Low — no new deps on Android; `Linking.openURL` already used for SMS/WhatsApp/tel.
- **Why Now:** UPI volume in India is over 12B transactions/month. Apps that don't integrate one-tap collect feel dated.

### N3. Per-Transaction Bill / Receipt Photo Attachments (MEDIUM VALUE)

- **Description:** Wire up the existing `Transaction.photoUri?` field in `mock.ts:25` — let users snap a photo of a receipt or handwritten note and attach it to any transaction.
- **Competitor:** Vyapar, myBillBook, Hisaabo, Spendrix all attach receipt photos to transactions. Payhawk and Emburse use OCR on the photo to auto-fill amount/date.
- **Value Proposition:** Shopkeepers get paper receipts (kirana delivery slips, supplier bills). Attaching the photo to the ledger entry makes the digital record self-contained — no "where's the original bill?" follow-ups.
- **Integration:**
  - The `Transaction.photoUri` field is already there.
  - Add a camera button next to the amount field in `add-transaction.tsx` (uses `expo-image-picker`, already a dep for QR codes).
  - Display the thumbnail on the transaction row in `party-detail.tsx` (tap to expand).
  - `StorageService.addTransaction()` already accepts the optional field; no schema migration.
- **Complexity:** Low–Medium — image picker, AsyncStorage URI persistence, gallery view. No OCR for v1.
- **Why Now:** The data model is ready; just no UI. 30–60 min to ship.

### N4. Daily / Weekly / Monthly Cash-Flow Summary on Dashboard (MEDIUM VALUE)

- **Description:** Add a small chart/timeline on the dashboard showing "Money In vs Money Out" for the current week or month.
- **Competitor:** Hisaabo, Spendrix, Vyapar, TallyPrime all surface a quick cash-flow widget on the home screen. Aukra's dashboard shows "Amount In/Out Today" + "Live closing balance."
- **Value Proposition:** Shopkeepers running a kirana store don't think in annual reports — they think "did I make money this week?" A 7-day bar chart is a fast answer.
- **Integration:**
  - New `cashFlowByDay(txs, days)` helper in `src/utils/ledger.ts` that buckets transactions by day.
  - Add a card to `(tabs)/index.tsx` between the totals banner and the party list. Use a minimal SVG bar chart inline (no chart library needed for 7 bars).
  - Toggle for "This Week" / "This Month" / "Last 30 Days".
- **Complexity:** Low — pure math + a 30-line chart component.
- **Why Now:** Existing dashboard is summary-card-only; this is the next click a shopkeeper makes after seeing the total.

### N5. Per-Party "Credit Limit" & Over-Limit Alerts (MEDIUM VALUE)

- **Description:** Let the shopkeeper set a `creditLimit?: number` per party. When a receivable crosses 80% of the limit, show a warning in the UI. When it crosses 100%, push a local notification (and surface in the dashboard).
- **Competitor:** Aukra's "Limit Exceeded" alert + Khatabook's customer-wise credit tracking.
- **Value Proposition:** The shopkeeper's actual risk-management today is mental. A shopkeeper who lets Ramesh build up to ₹2L of credit with no signal has a real bad-debt risk. A soft warning ("Ramesh is at 95% of his ₹20,000 limit") gives them a moment to pause before extending more.
- **Integration:**
  - Add `creditLimit?: number` to `Party` type in `mock.ts`.
  - Add optional field in `add-party.tsx` form.
  - Compute `usage = (balance / limit) * 100` in `partyBalance()` and expose.
  - Color the balance banner in `party-detail.tsx` orange at ≥80%, red at ≥100%.
  - Show a dashboard tile "Parties Over Limit" with the count.
- **Complexity:** Low — small data model change, threshold coloring, one new tile.
- **Why Now:** Aukra markets this aggressively; it's a thin add to CredEasy.

### N6. Bulk SMS / WhatsApp Reminder to All Overdue Parties (MEDIUM VALUE)

- **Description:** A "Remind All Overdue" button on the dashboard that opens WhatsApp Web/App with all overdue-party messages queued (or sends SMS via `expo-sms`).
- **Competitor:** OkCredit's "Send reminders to all" one-tap action. Khatabook's batch reminder. BizBeat's collection campaigns.
- **Value Proposition:** The current "Remind" is per-party. For a shopkeeper with 30 overdue parties at month-end, that's 30 taps. One-tap batch is a real time-saver and the natural monetization surface ("Send 100 reminders/mo — Pro feature").
- **Integration:**
  - `Linking.openURL('whatsapp://send?text=...')` only opens a single chat. For multi-recipient, use a loop that opens sequentially with a small delay (or opens WhatsApp Web with a generated CSV).
  - Simpler MVP: build a multi-select on the dashboard, then loop `Linking.openURL` with throttling.
  - Better: generate a per-party "reminder card" image (uses existing PDF pipeline or a small canvas) and pre-fill WhatsApp with it.
- **Complexity:** Medium — UX design of multi-select + throttled opening or a true multi-recipient SMS gateway integration.
- **Why Now:** Khatabook's "free batch reminder" was historically their #1 growth hook. OkCredit copied it. Aukra now offers it as "AI-powered voice calls for persistent cases" — i.e., they automated the phone-call follow-up too. CredEasy can ship a simpler version fast.

### N7. AI Voice Calls for Persistent Overdue (LOW-MEDIUM VALUE, niche)

- **Description:** When a WhatsApp reminder goes unread for X days, offer to place an AI-voice call to the customer (in Hindi) that reads the balance and asks for a payment date.
- **Competitor:** Aukra's headline 2026 feature: "AI voice call alerts for persistent cases."
- **Value Proposition:** Voice gets through where text gets ignored. For a ₹500 udhar 90 days overdue, a call is the right escalation.
- **Integration:**
  - Backend route: `POST /api/voice/call` that takes a phone + message and uses an Exotel/AISpeech/Vapi integration.
  - Frontend: dashboard widget "Schedule voice follow-up" with date picker + message template.
- **Complexity:** High — requires a paid telephony provider, account setup, regulatory compliance (TRAI DLT registration for Indian SMS/calls).
- **Why Now:** It's a clear differentiation but heavy. Park until cloud sync ships.

### N8. Multi-Language Expansion Beyond English/Hindi (LOW-MEDIUM VALUE)

- **Description:** The `i18n` object currently has 2 languages. Add Tamil, Telugu, Marathi, Gujarati, Bengali, Kannada, Punjabi — the 7 other major Indian languages.
- **Competitor:** Aukra: 12+ languages. Khatabook: 12. AiXpense: 22. VoiceKhata: 12.
- **Value Proposition:** Language is a real differentiator in tier-2/3 India. A Tamil shopkeeper who can't read English is excluded by every "Settings → English only" toggle.
- **Integration:**
  - `src/i18n.ts` already has a dictionary pattern. Just expand `translations` with each new language.
  - Persist via `StorageService.getLanguage/setLanguage` (already in place).
  - Voice assistant system prompt already supports `lang` parameter — extend backend's `VOICE_SYSTEM_PROMPT` to handle more languages.
  - Translations can be done with community help or LLM-assisted draft + human review.
- **Complexity:** Low per language once i18n is set up; ~30 keys each.
- **Why Now:** The architecture is ready. VoiceKhata's entire pitch is "speak in your language" and CredEasy's voice assistant is genuinely good — but the UI is locked to English/Hindi.

### N9. Staff / Sub-User Accounts (LOW VALUE for v1, HIGH for scale)

- **Description:** Let the business owner invite a helper who can log transactions but not see total balance, profit, or cloud-sync.
- **Competitor:** Khatabook explicitly markets this as a reason to choose them over OkCredit. Role-based accounts (owner, cashier, viewer).
- **Value Proposition:** A shop with two helpers logging entries can't safely share a single phone PIN. A staff account with restricted visibility is the answer.
- **Integration:**
  - New `StaffAccount` type and storage.
  - Owner generates invite code; staff installs app and enters code.
  - Different nav: staff sees only "+Add Entry" + recent parties, no dashboard totals, no settings.
- **Complexity:** High — requires Supabase auth changes (multiple users per business) which is in the Tier-4 cloud-sync workstream. Defer until then.
- **Why Now:** Real, but blocked on the cloud-sync workstream.

### N10. Credit Days Tracking (MEDIUM VALUE)

- **Description:** Set `creditDays?: number` per party (e.g., 30). The system tracks "days since oldest unpaid DEBIT" and flags any party past their credit days.
- **Competitor:** Aukra surfaces "Credit Days Expired" as a dashboard tile. TallyPrime has aging buckets. BizBeat flags "supplier X is now 47 days past credit."
- **Value Proposition:** The 30/60/90 aging bucket concept in the original FEATURES list is the same idea — but a simpler "credit days per party" framing is more usable for kirana shops.
- **Integration:**
  - Add `creditDays?: number` to `Party` type.
  - In `partyBalance()` or a new `daysOverCredit(party, txs)` helper, compute the age of the oldest un-CREDITed DEBIT.
  - Dashboard widget "Credit Days Expired" with count + list (similar to N4's pattern).
  - Pair with N6's "Remind All Overdue" for a complete collections workflow.
- **Complexity:** Low — small data model + one helper + one widget.
- **Why Now:** Pairs naturally with the existing `REMIND` action and WhatsApp share. Could ship in the same week as N5/N6.

### N11. Profit & Loss Statement (Quick Books style) (MEDIUM VALUE)

- **Description:** Generate a monthly P&L: opening balance + all "GOT" (income) - all "GAVE" (expense) - any "SUPPLIER" balance changes = closing balance.
- **Competitor:** Vyapar, myBillBook, Hishabee, TallyPrime all auto-generate P&L. Hishabee's homepage literally says "live cost reports from all your different outlets on one single mobile dashboard."
- **Value Proposition:** Shopkeepers filing GST, talking to their CA, or applying for a loan need a P&L. Today they have to compute it manually from the ledger.
- **Integration:**
  - New `computePnL(txs, period)` in `src/utils/ledger.ts` that filters by date range and buckets by `partyType` (CUSTOMER = revenue, SUPPLIER = expense).
  - Add a "Profit & Loss" card to `reports.tsx` showing month-to-date and last-3-months.
  - Include in PDF export.
- **Complexity:** Low — pure math, one helper, one card.
- **Why Now:** The data is all already in the ledger. Just a derivation.

### N12. "Today's Collection" / "Today's Sales" Dashboard Tile (LOW VALUE but HIGH visibility)

- **Description:** Two prominent tiles on the dashboard: "Today's Sales (₹)" and "Today's Collection (₹)". Updates with each new transaction.
- **Competitor:** Aukra's "Amount In/Out Today" widget. Hishabee's multi-store live cost reports. Vyapar's daily cash book.
- **Value Proposition:** A shopkeeper who only opens the app once a day wants the day's summary first, not the all-time total. This is a 5-min glance test.
- **Integration:**
  - `todaysTotal(txs, type)` helper: sum of today's `GOT` and today's `DEBIT`.
  - Render two stat tiles at the very top of `(tabs)/index.tsx`, above the existing "Total Receivable / Payable" banner.
- **Complexity:** Very Low — 10 lines of code.
- **Why Now:** Trivial to add; high perceived value because it's the first thing the user sees.

---

## Cross-Cutting Trend Notes (2026)

Three things that came up repeatedly across 2025-2026 competitor updates that aren't single features but worth noting:

1. **AI is now table-stakes, not premium.** Aukra, Khatabook (interest calculator), BizBeat, VoiceKhata, AiXpense all ship AI features on the free tier. CredEasy's voice assistant is already genuinely strong but should be marketed as AI-first, not as a Premium feature. Consider promoting it from the paywall.

2. **Auto-reminders + auto-collections are the new battleground.** Aukra and Khatabook are pushing hard on "you don't need to chase — we do." CredEasy's REMIND action is a one-shot; competitors are doing scheduled, batch, and AI-call follow-ups. N6 + N10 + N7 form a complete story; even shipping N6 + N10 alone is a major UX upgrade.

3. **Dynamic UPI / payment-link generation is everywhere.** Razorpay, Aukra, Vyapar, myBillBook, Hishabee all generate per-invoice UPI links/QRs. N2 is the lowest-hanging fruit here — 30 minutes of code, immediate user value, fits the existing WhatsApp pattern.

---

## Updated Prioritization Recommendation

**Implement first (next 2–3 sessions):**
- N2 — UPI Collect Link (30 min) — lowest complexity, immediate value
- N12 — Today's Sales/Collection tiles (15 min) — trivial, high visibility
- N3 — Receipt photo on transactions (1 hour) — model is already there
- N5 — Credit limit + alert (1 hour) — small data model change
- N4 — Cash-flow chart on dashboard (1.5 hours) — answers the "did I make money?" question

**Implement second (next 2 weeks):**
- N1 — Auto interest calculation
- N6 — Batch WhatsApp reminders
- N10 — Credit days tracking
- N11 — P&L report
- #4 — CSV export
- #3 — Bill history
- #11 — JSON backup/restore (critical given cloud sync is broken)

**Decide based on user feedback:**
- N8 — Multi-language expansion (depends on target market)
- #12 — Dark mode
- N9 — Staff accounts (defer to post cloud-sync)

**Hold for after cloud sync ships:**
- N7 — AI voice calls
- N9 — Staff accounts (architectural)
- #18 — Inventory
- #20 — Aging report (or ship as part of N10's credit-days)
- #21 — SMS auto-parsing

---

*Last updated: 2026-09-03 — competitor research refresh*
*Competitors surveyed: OkCredit, Khatabook, Vyapar, TallyPrime, myBillBook, Hishabee, Aukra, AiXpense, BizBeat, VoiceKhata, Udharbook AI, Razorpay UPI, EnKash.*
