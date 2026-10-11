# Voice Assistant Provider Setup

Chotu's language model, transcription, and speech synthesis are configured on
the backend. Do not put provider credentials in the mobile app.

## Google Cloud Speech

1. Select a Google Cloud project and enable the Cloud Speech-to-Text API and
   Cloud Text-to-Speech API.
2. Give the backend runtime identity the Cloud Speech Client
   (`roles/speech.client`) and Cloud Text-to-Speech User
   (`roles/texttospeech.user`) roles.
3. Set `GOOGLE_CLOUD_PROJECT` to the project ID. For local development using a
   service-account key file, set `GOOGLE_APPLICATION_CREDENTIALS` to its
   absolute path. In production, prefer the host's attached service identity or
   a secret-managed credentials file; never commit a service-account key.

On native builds, transcription uses Speech-to-Text v2's `chirp_3` streaming
recognition with 16 kHz mono PCM frames, interim results, and client-side
adaptive voice-activity detection. The detector calibrates over a rolling
five-second noise window, requires several consecutive frames above the
noise-relative onset threshold, and uses hysteresis to avoid treating steady
background noise as ongoing speech. It requires four consecutive 100 ms frames
above a stronger adaptive onset threshold before declaring speech and ends the
stream after 450 ms without detected speech. This favors clear, close speech
over quiet-room speech; eight preroll frames preserve the beginning of commands
while the onset gate is satisfied. Web recording uses a -32 dB threshold,
three consecutive 100 ms meter samples, and the same 450 ms end-silence wait.
These level-based gates reject steady room noise and brief spikes, but cannot
reliably distinguish speech-like background audio from the user's voice. PCM
stays in memory during
streaming; if the WebSocket is unavailable, the app writes a temporary WAV in
its private cache, uploads it, and deletes it after the request. The native stream
requires a development or production build that includes
`react-native-audio-api`; it is not available in Expo Go. Android builds also
package the ABI-matched Oboe shared library required by the audio module; the
release APK must contain both `libreact-native-audio-api.so` and `liboboe.so`.
The backend must install the `websockets` dependency so Uvicorn can accept the
native WebSocket connection. Chirp 3 requests use the `asia-southeast1` Speech
location by default; set `GOOGLE_CLOUD_SPEECH_LOCATION` only to a location that
supports Chirp 3, and use the matching regional Speech API endpoint.
The deployed backend must include `/api/voice/transcribe/stream` to get interim
transcripts and avoid the upload fallback; an older deployment can still
transcribe the captured WAV through `/api/voice/transcribe`.
Web transcription continues to use the upload endpoint with automatic audio
decoding. Indian English and Hindi are configured for recognition; the
recognized language code is carried into the assistant/TTS request so the app's
display-language setting cannot force a Hindi reply through the English voice.
Chirp 3 does not support prebuilt phrase-set adaptation, so custom ledger-name
hints are not sent as an unsupported config. If native
streaming cannot establish its WebSocket connection, Chotu continues capturing
the same 16 kHz PCM stream, wraps it in WAV, and submits it to
`/api/voice/transcribe`; this uses Google Cloud when configured and does not
switch providers after a configured Google failure. Automatic pause detection
uses a short preroll, an adaptive noise floor, a stronger bounded onset
threshold, and a multi-frame speech-activity gate. Brief background sounds and
energy below the calibrated speech threshold do not activate capture or refresh
the end-of-speech timer. The shorter 450 ms wait submits promptly after speech
ends, at some risk of treating a long within-command pause as the end. This
avoids waiting indefinitely on
intermittent noise without polling Expo's recorder after native capture stops.
After end-of-speech auto-submit or a user tap on the in-app mic control, native
capture is stopped before transcription and assistant processing begin. The
widget's **Stop** action cancels capture and stops its foreground service before
session validation. Microphone capture remains stopped throughout TTS playback and resumes after
the reply finishes; user speech is not captured over Chotu's response.

Each authenticated account has a shared 20-request budget per 60-second fixed
window across the voice endpoints, enforced by the
`consume_voice_request_limit` Supabase RPC and backed by a local
early-rejection limit. Current business workspaces are owner-only, so the
shared account cap also bounds any one workspace and is stricter across
multiple workspaces. Apply the updated
`docs/enable-transaction-realtime.sql` before deploying this backend change.
Repeated provider failures open a per-backend-instance circuit for 30 seconds;
the first request after cooldown is the half-open probe. Provider timeouts,
disabled retries, and the global quota constrain cost; the circuit itself is
instance-local, not a distributed provider-health signal.

Backend API failures and requests taking at least two seconds are written to
Cloud Run logs without transcript or ledger content. Configure Cloud Logging
alerts on the `API request failed` and `Slow API request` messages for
production monitoring.

Synthesis uses Cloud Text-to-Speech and returns MP3 audio. Hindi replies use
Google's male Indian `hi-IN-Chirp3-HD-Puck` voice and Indian-English replies
use male `en-IN-Chirp3-HD-Puck`, both at a measured speaking rate of 0.98.
Explicit rupee amounts are converted into language-matched Indian number words
before synthesis, including paise, so balances and transaction values are
spoken clearly instead of being read as grouped digits or a currency symbol.
Grouped numbers without a currency marker are also expanded to number words so
the speech engine does not treat a thousands separator as a spoken pause (for
example, `46,500` becomes “forty six thousand five hundred” and `₹66,254`
becomes “sixty six thousand two hundred fifty four rupees”). These backend TTS
changes require deploying the updated backend before they reach users.
Hindi is selected from the spoken reply's Devanagari text even when the app UI
language is English. The response includes non-secret provider, language and
voice headers; the app logs these so a stale deployment or legacy TTS fallback
can be distinguished from the requested Google voice. Chirp 3 HD does not use
the old WaveNet pitch setting. The Expo file recorder is
isolated to web; native screens only use the PCM capture recorder. A silent
native listen retries while the user-started conversation remains active.
These backend-side voice changes require deploying the backend as well as
installing the updated app.

## Response latency

The assistant sends at most the three most recent conversation turns to Gemini,
caps a generated reply at 192 tokens, and does not retry a timed-out interactive
completion. The upstream request timeout is four seconds; if the provider is
slower, the backend returns an error instead of waiting through another attempt.
Google TTS likewise has a three-second RPC deadline and automatic retries are
disabled. Streaming transcription finalization is bounded to 1.25 seconds and
returns any interim transcript before using the existing upload fallback. Auth
verification reuses a process-scoped HTTP connection pool and is bounded to
2.5 seconds. Voice route, model,
and synthesis durations are logged without transcripts or business data, and
HTTP voice responses include a backend-duration diagnostic header. These limits
reduce avoidable waiting but cannot guarantee an instant reply: provider
generation, speech synthesis, network conditions, and device audio playback
still contribute. Native builds must be rebuilt to use the stricter speech gate
and shorter 450 ms end-of-speech wait.

## Cost controls

Chotu keeps the current Gemini model and Chirp 3 HD voice to preserve answer and
speech quality. Before each model request, the backend removes internal record
IDs and unused fields from the ledger context while keeping all answer-relevant
party, transaction, inventory, and movement data. It also serializes that
context compactly. The repeated action schema was removed from the model prompt
without changing supported actions or confirmation rules. Model logs include
provider-reported prompt/completion token counts when available and context
character counts; TTS logs already include the text character count. Streaming
transcription logs processed audio seconds from the received 16 kHz mono PCM
byte count. These measurements contain no
transcript or business content. Use Google Cloud Billing Reports grouped by
service and SKU to confirm which service is consuming credits; model
input/output tokens, speech audio duration, and synthesized character volume
have separate costs. Do not infer credit use from latency logs alone.

## Voice party creation

When a user explicitly asks Chotu to add a party by name, the backend emits a
party-creation action directly. The app requests Contacts access only for that
party-creation flow, checks the complete readable contact list for an exact
normalized name match, and uses a single matching Indian mobile number
automatically. If access is denied or there is no exact match, Chotu asks for a
10-digit number or “skip”. Ledger entry and edit flows do not request Contacts
access. Microphone permission is requested only when the user starts recording,
as required by Android.

## Gemini on Vertex AI

Chotu can use Gemini on Vertex AI with the Cloud Run runtime service identity;
no API key or service-account key file is needed. Set `GEMINI_PROVIDER=vertex`,
`GOOGLE_CLOUD_PROJECT` to the billable project ID, `VERTEX_AI_LOCATION` to a
supported model location, and `GEMINI_MODEL` to a model available to that
project. Chotu uses `gemini-2.5-flash-lite` on Vertex AI in `us-central1`.
Google lists this model as generally available in that region through its
October 20, 2026 retirement date ([model lifecycle](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions)).
Plan to move to a supported replacement before then. Grant the Cloud Run runtime service account
`roles/aiplatform.user` and enable the Vertex AI API. The backend uses
Application Default Credentials and the Vertex AI OpenAI-compatible Chat
Completions endpoint; it sends Chotu's JSON response mode and never falls back
to another provider on failure.

The production Cloud Run service keeps one minimum instance warm to reduce
cold-start delays for infrequent voice sessions. This incurs ongoing idle
instance charges. Recent production request logs showed about 1.6–2.5 seconds
for the assistant response and 1.0–1.6 seconds for the separate TTS request;
model generation and speech synthesis remain provider-dependent.

The Google Cloud $300 Free Trial Welcome credit can apply to eligible Vertex
AI usage, but Google explicitly excludes Gemini API in AI Studio from that
credit. AI Studio billing/prepay is a separate product and balance; its HTTP
402 `prepayment credits are depleted` response is not fixed by claiming Cloud
credits. See [Google Cloud Free Trial restrictions](https://docs.cloud.google.com/free/docs/free-cloud-features),
[Vertex AI OpenAI-compatible authentication](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/migrate/openai/auth-and-credentials),
and [Vertex AI model pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing).

For local or legacy AI Studio use, set `GEMINI_PROVIDER=ai-studio` and
`GEMINI_API_KEY`; this path does not use Google Cloud trial credits.

Existing transcription and synthesis providers are used only while
`GOOGLE_CLOUD_PROJECT` is unset. Once Google Cloud is configured, provider
errors are returned to the app rather than silently switching providers.
