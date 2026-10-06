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
background noise as ongoing speech. It ends the stream after 850 ms of detected
silence. The minimum speech-onset RMS is 0.0025 for quiet-room speech, while
the rolling noise-relative threshold and three consecutive onset frames still
filter steady background noise. PCM stays in memory during
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
uses a short preroll, an adaptive noise floor, a lower bounded onset threshold,
and a multi-frame speech-activity gate. Brief background sounds and energy below
the calibrated speech threshold no longer refresh the end-of-speech timer,
while quieter speech remains detectable. This avoids waiting indefinitely on
intermittent noise without polling Expo's recorder after native capture stops.
Microphone capture remains stopped throughout TTS playback and resumes after
the reply finishes; user speech is not captured over Chotu's response.

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

## Voice party creation

When a user explicitly asks Chotu to add a party by name, the backend emits a
party-creation action directly. The app requests Contacts access only for that
party-creation flow, checks the complete readable contact list for an exact
normalized name match, and uses a single matching Indian mobile number
automatically. If access is denied or there is no exact match, Chotu asks for a
10-digit number or “skip”. Ledger entry and edit flows do not request Contacts
access. Microphone permission is requested only when the user starts recording,
as required by Android.

## Gemini

Set `GEMINI_API_KEY` on the backend to enable Gemini assistant replies.
`GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`. The backend maps the
retired `gemini-2.5-flash-lite` setting to this model for existing deployments.

Existing transcription and synthesis providers are used only while
`GOOGLE_CLOUD_PROJECT` is unset. Once Google Cloud is configured, provider
errors are returned to the app rather than silently switching providers.
