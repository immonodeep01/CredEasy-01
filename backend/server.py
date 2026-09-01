from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Header, Depends
from starlette.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
import groq
import httpx
import json
import math
import os
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# Configured before anything else so import-time failures below are logged
# rather than raising NameError on `logger`.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase issues and signs the app's session tokens, so this server verifies
# them rather than minting its own. The anon key is public by design — it is
# sent as the `apikey` header Supabase's auth API requires, not as a secret.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Add your routes to the router instead of directly to app
VOICE_RATE_LIMIT_PER_MINUTE = 20
VOICE_RATE_LIMIT_WINDOW_SECONDS = 60
USER_RATE_LIMIT_BUCKETS = defaultdict(list)
# Buckets are swept only once the dict grows past this, so the common path stays
# O(1). Without any eviction it gained one list per user for the process's life.
MAX_RATE_LIMIT_BUCKETS = 10_000

UPSTREAM_TIMEOUT_SECONDS = 10.0
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_TRANSCRIPT_LEN = 2000
MAX_CONTEXT_CHARS = 64 * 1024
MAX_REPLY_LEN = 4000
MAX_ACTIONS = 2
MAX_NAME_LEN = 100
MAX_NOTE_LEN = 200
MAX_PHONE_LEN = 20
ALLOWED_ROUTES = {"dashboard", "parties", "billing", "reports", "settings"}


class VoiceAssistRequest(BaseModel):
    transcript: str = Field(default="", max_length=MAX_TRANSCRIPT_LEN)
    context: Dict[str, Any] = Field(default_factory=dict)
    lang: str = Field(default="en", max_length=8)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class SpeakRequest(BaseModel):
    text: str = Field(default="", max_length=2000)
    lang: str = Field(default="en", max_length=8)


async def get_authenticated_user(authorization: Optional[str] = Header(None)) -> dict:
    """Resolve the current user from a Supabase access token. Raises 401, never 403.

    This replaces a second, parallel session system: the server used to mint its
    own `st_...` tokens into db.user_sessions, while the app only ever held a
    Supabase JWT. The two could never agree, so every authenticated route
    rejected every request. Asking Supabase to validate its own token leaves one
    source of truth and lets the Mongo users/user_sessions collections go away.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        # A misconfigured server must not masquerade as a rejected user, or the
        # whole fleet looks like every shopkeeper's token expired at once.
        logger.error("SUPABASE_URL / SUPABASE_ANON_KEY are not configured")
        raise HTTPException(status_code=500, detail="Authentication is not configured on the server")

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as httpx_client:
            resp = await httpx_client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": SUPABASE_ANON_KEY},
            )
    except Exception:
        # 503, not 401: "we could not check" is not "your token is bad", and
        # returning 401 for a network blip signs the user out of the app.
        logger.exception("Supabase token verification request failed")
        raise HTTPException(status_code=503, detail="Could not verify your session. Please try again.")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    try:
        data = resp.json()
    except ValueError:
        logger.error("Supabase /auth/v1/user returned a non-JSON body")
        raise HTTPException(status_code=502, detail="Could not verify your session. Please try again.")

    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Could not verify your session. Please try again.")

    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    metadata = data.get("user_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "user_id": str(user_id),
        "email": data.get("email") or "",
        "name": metadata.get("full_name") or metadata.get("name") or "",
        "picture": metadata.get("avatar_url"),
    }


def _evict_stale_rate_limit_buckets(now: float, window_seconds: int) -> None:
    if len(USER_RATE_LIMIT_BUCKETS) <= MAX_RATE_LIMIT_BUCKETS:
        return
    stale = [
        user_id for user_id, timestamps in USER_RATE_LIMIT_BUCKETS.items()
        if not timestamps or now - timestamps[-1] >= window_seconds
    ]
    for user_id in stale:
        del USER_RATE_LIMIT_BUCKETS[user_id]


def enforce_user_rate_limit(user_id: str, limit: int = VOICE_RATE_LIMIT_PER_MINUTE, window_seconds: int = VOICE_RATE_LIMIT_WINDOW_SECONDS):
    now = time.monotonic()
    _evict_stale_rate_limit_buckets(now, window_seconds)
    timestamps = USER_RATE_LIMIT_BUCKETS[user_id]
    timestamps[:] = [ts for ts in timestamps if now - ts < window_seconds]
    if len(timestamps) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again shortly.")
    timestamps.append(now)


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(get_authenticated_user)):
    return {
        "user": {
            "user_id": user["user_id"],
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
        }
    }


@api_router.delete("/auth/account")
async def delete_account(user: dict = Depends(get_authenticated_user)):
    """Delete the authenticated user's account from Supabase Auth.

    This endpoint requires the SUPABASE_SERVICE_ROLE_KEY environment variable.
    Without it, this endpoint returns 500.
    """
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not service_role_key:
        logger.error("SUPABASE_SERVICE_ROLE_KEY is not configured")
        raise HTTPException(status_code=500, detail="Account deletion is not configured on the server")

    user_id = user["user_id"]

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT_SECONDS) as httpx_client:
            resp = await httpx_client.delete(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {service_role_key}",
                    "apikey": service_role_key,
                    "Content-Type": "application/json"
                },
            )

        if resp.status_code in (200, 204):
            return {"success": True, "message": "Account deleted successfully"}
        else:
            logger.error(f"Failed to delete account: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=500, detail="Failed to delete account. Please try again.")

    except Exception as e:
        logger.exception("Account deletion request failed")
        raise HTTPException(status_code=500, detail="Could not delete account. Please try again.")


@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.get("/debug/groq")
async def debug_groq():
    """Diagnostic endpoint to verify which Groq models are accessible."""
    api_key = get_groq_api_key()
    if not api_key:
        return {"groq_configured": False, "reason": "GROQ_API_KEY not set"}
    try:
        client = get_groq_client()
        models_response = await client.models.list()
        all_models = [m.id for m in models_response.data]
        return {
            "groq_configured": True,
            "key_length": len(api_key),
            "all_models": all_models,
            "count": len(all_models),
        }
    except Exception as e:
        return {"groq_configured": True, "error": str(e), "key_length": len(api_key)}


# ---------------------------------------------------------------------------
# Voice Assistant: Whisper transcription + LLM intent parsing
# ---------------------------------------------------------------------------
ALLOWED_AUDIO_EXT = {".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".wav", ".webm"}

_openai_client: Optional[AsyncOpenAI] = None
_groq_client: Optional[groq.AsyncGroq] = None


def get_groq_api_key() -> Optional[str]:
    """Groq is the primary provider — free tier, no credit card needed.
    Used for chat completions and Whisper transcription."""
    key = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_APIKEY") or None
    if key:
        logger.info(f"GROQ_API_KEY found (length={len(key)})")
    else:
        logger.warning("GROQ_API_KEY not found in environment")
    return key


def get_openai_api_key() -> Optional[str]:
    """OpenAI is the fallback if Groq is unavailable or exhausted."""
    return (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("EMERGENT_LLM_KEY")
        or None
    )


def get_groq_client() -> groq.AsyncGroq:
    global _groq_client
    if _groq_client is None:
        api_key = get_groq_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")
        _groq_client = groq.AsyncGroq(api_key=api_key)
    return _groq_client


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = get_openai_api_key()
        if not api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


@api_router.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...), user: dict = Depends(get_authenticated_user)):
    enforce_user_rate_limit(str(user["user_id"]))

    suffix = Path(file.filename or "recording.m4a").suffix.lower() or ".m4a"
    if suffix not in ALLOWED_AUDIO_EXT:
        raise HTTPException(status_code=415, detail=f"Unsupported audio format: {suffix}")

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio must be 25 MB or smaller")

    # Try Groq first (free Whisper), fall back to OpenAI.
    last_error = None
    if get_groq_api_key():
        try:
            groq_client = get_groq_client()
            result = await groq_client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",  # faster, free tier model
                file=(f"recording{suffix}", audio),
                prompt="Hindi and English (Hinglish) shopkeeper ledger speech. Preserve names, numbers and rupee amounts.",
            )
            return {"text": getattr(result, "text", "") or ""}
        except Exception as e:
            logger.warning("Groq transcription failed, falling back to OpenAI: %s", e)
            last_error = e

    if get_openai_api_key():
        try:
            openai_client = get_openai_client()
            result = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=(f"recording{suffix}", audio),
                prompt="Hindi and English (Hinglish) shopkeeper ledger speech. Preserve names, numbers and rupee amounts.",
            )
            return {"text": getattr(result, "text", "") or ""}
        except Exception as e:
            logger.exception("OpenAI transcription failed")
            last_error = e

    logger.exception("transcription failed: no provider succeeded")
    raise HTTPException(status_code=502, detail="Could not transcribe the recording. Please try again.")


@api_router.post("/voice/speak")
async def voice_speak(payload: SpeakRequest, user: dict = Depends(get_authenticated_user)):
    """Synthesize text to speech and stream the MP3 back.

    Uses Edge TTS (free, no API key) for TTS, with OpenAI as fallback.
    Returns audio as a streaming response so the client can play() while
    bytes are still arriving. If TTS fails for any reason, the assistant's
    on-screen text reply still works — speech is a progressive enhancement.
    """
    enforce_user_rate_limit(str(user["user_id"]))

    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    text = text[:2000]

    # Pick a voice that handles Hindi + English well. Edge TTS voices are free.
    lang = (payload.lang or "en").lower()
    # Hindi voices: hi-IN-SwaraNeural (female), hi-IN-MadhurNeural (male)
    # English voices: en-US-JennyNeural, en-US-GuyNeural
    if lang.startswith("hi"):
        voice = "hi-IN-SwaraNeural"
    else:
        voice = "en-US-JennyNeural"

    # Try Edge TTS first (completely free, no API key needed)
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        # Generate to bytes
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        if audio_bytes:
            return StreamingResponse(
                iter([audio_bytes]),
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline"},
            )
    except ImportError:
        logger.warning("edge-tts not installed, trying fallback")
    except Exception as e:
        logger.warning("Edge TTS failed, trying OpenAI fallback: %s", e)

    # Fallback to OpenAI if available
    if get_openai_api_key():
        try:
            model = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
            openai_client = get_openai_client()
            response = await openai_client.audio.speech.with_streaming_response.create(
                model=model,
                voice="alloy",
                input=text,
                response_format="mp3",
            )
            return StreamingResponse(
                response.iter_bytes(),
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline"},
            )
        except Exception:
            logger.exception("OpenAI TTS failed")

    raise HTTPException(status_code=502, detail="Could not synthesize speech. Please try again.")


VOICE_SYSTEM_PROMPT = """You are CredEasy Assistant, a voice helper inside CredEasy — a digital khata (credit ledger) app used by small Indian shopkeepers.
The user speaks Hindi, English or Hinglish. You do three things:
1. RECORD entries: e.g. "Ramesh ko 500 rupaye udhaar diye" -> add a GAVE transaction of 500 for party Ramesh.
2. ANSWER questions about the ledger using the CONTEXT provided: e.g. "Ramesh ka kitna baaki hai?".
3. GUIDE / navigate the user through the app: e.g. "bill kaise banau" -> explain briefly and navigate to billing.

Reply ONLY with a single JSON object, no markdown, no code fences:
{
  "reply": "<short spoken-style answer, max 2 sentences, in the SAME language the user used>",
  "actions": [ ... ]
}

Allowed actions (0 to 2 items):
{"type":"ADD_TRANSACTION","partyName":"<name as spoken>","amount":<number>,"txType":"GAVE"|"GOT","note":"<short note or empty>"}
   - GAVE = shopkeeper gave goods/credit (money receivable). GOT = shopkeeper received payment.
{"type":"ADD_PARTY","name":"<name>","phone":"<10 digits or empty>","partyType":"CUSTOMER"|"SUPPLIER"}
{"type":"NAVIGATE","route":"dashboard"|"parties"|"billing"|"reports"|"settings"}
{"type":"REMIND","partyName":"<name>"}

Rules:
- Only emit ADD_TRANSACTION when an amount AND a party are clearly stated. Otherwise ask for what is missing in "reply" with an empty actions array.
- If the user says something vague ("do something for Ramesh", "update that", "batao"), ask a clarifying question in the SAME language before acting. Do not guess.
  Example: user says "Ramesh ko 500 diye" but no Ramesh exists → ask "Kaunsa Ramesh? Ramesh Kumar ya Ramesh Sharma?"
  Example: user says "uska baaki check karo" → ask "Kaunsa customer ka baaki?"
- Match partyName to the closest existing party name from CONTEXT when possible.
- For pure questions, answer with numbers from CONTEXT and return an empty actions array.
- Amounts are Indian rupees; convert words like "paanch sau" to 500.
- Never invent balances that are not in CONTEXT.
"""


def _clean_str(value: object, max_len: int) -> str:
    if not isinstance(value, str):
        value = "" if value is None else str(value)
    return value.strip()[:max_len]


def _clean_amount(value: object) -> Optional[float]:
    """A positive, finite rupee amount, or None. Rejects NaN, infinity and
    "1e999" — any of which would poison every balance the party appears in."""
    if isinstance(value, bool):
        return None
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(amount) or amount <= 0:
        return None
    return round(amount, 2)


def sanitize_actions(raw: object) -> List[dict]:
    """The model's output is untrusted input: the app writes these actions
    straight into the shopkeeper's ledger. Emit only whitelisted shapes with
    coerced, length-capped fields and drop anything that does not fit."""
    if not isinstance(raw, list):
        return []
    actions: List[dict] = []
    for item in raw[:MAX_ACTIONS]:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "ADD_TRANSACTION":
            amount = _clean_amount(item.get("amount"))
            party = _clean_str(item.get("partyName"), MAX_NAME_LEN)
            tx_type = item.get("txType")
            if amount is None or not party or tx_type not in ("GAVE", "GOT"):
                continue
            actions.append({
                "type": kind,
                "partyName": party,
                "amount": amount,
                "txType": tx_type,
                "note": _clean_str(item.get("note"), MAX_NOTE_LEN),
            })
        elif kind == "ADD_PARTY":
            name = _clean_str(item.get("name"), MAX_NAME_LEN)
            if not name:
                continue
            actions.append({
                "type": kind,
                "name": name,
                "phone": _clean_str(item.get("phone"), MAX_PHONE_LEN),
                "partyType": "SUPPLIER" if item.get("partyType") == "SUPPLIER" else "CUSTOMER",
            })
        elif kind == "NAVIGATE":
            route = _clean_str(item.get("route"), 32)
            if route not in ALLOWED_ROUTES:
                continue
            actions.append({"type": kind, "route": route})
        elif kind == "REMIND":
            party = _clean_str(item.get("partyName"), MAX_NAME_LEN)
            if not party:
                continue
            actions.append({"type": kind, "partyName": party})
    return actions


@api_router.post("/voice/assist")
async def voice_assist(payload: VoiceAssistRequest, user: dict = Depends(get_authenticated_user)):
    enforce_user_rate_limit(str(user["user_id"]))

    transcript = payload.transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="transcript is required")

    # The ledger context is pasted verbatim into the prompt, so an oversized one
    # is a token-cost amplifier as much as a memory concern.
    context_json = json.dumps(payload.context, ensure_ascii=False, default=str)
    if len(context_json) > MAX_CONTEXT_CHARS:
        raise HTTPException(status_code=413, detail="Ledger context is too large to send.")

    user_text = f"CONTEXT (current ledger):\n{context_json}\n\nUSER SAID: {transcript}"

    messages: List[Dict[str, str]] = [{"role": "system", "content": VOICE_SYSTEM_PROMPT}]
    # Include last 6 conversation turns so the model can ask clarifying questions.
    for turn in payload.history[-6:]:
        messages.append({"role": "user", "content": turn.get("user", "")})
        if turn.get("assistant"):
            messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": user_text})

    text = ""
    last_error = None

    # Try Groq first (free Llama), fall back to OpenAI
    if get_groq_api_key():
        try:
            groq_client = get_groq_client()
            # Discover the first available chat model on the account — Groq has
            # changed model names over time and "not found" on the right tier
            # is the most common reason a free key stops working.
            available_models = []
            try:
                models_response = await groq_client.models.list()
                # Accept any model that could be a chat model, including namespaced ones
                available_models = [
                    m.id for m in models_response.data
                    if any(tag in m.id.lower() for tag in [
                        "llama", "mixtral", "gemma", "qwen", "allam", "compound", "gpt-oss"
                    ])
                ]
            except Exception as e:
                logger.warning("Could not list Groq models: %s", e)

            # Prefer smaller/faster models first; all are free tier on Groq.
            # Models prefixed with "groq/", "openai/" etc. need the full ID.
            preferred = [
                "qwen/qwen3.8-27b",
                "qwen/qwen3.6-27b",
                "allam-2-7b",
                "groq/compound-mini",
                "groq/compound",
                "openai/gpt-oss-20b",
                "openai/gpt-oss-120b",
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
            ]
            chosen_model = None
            for p in preferred:
                if p in available_models:
                    chosen_model = p
                    break
            if not chosen_model and available_models:
                chosen_model = available_models[0]

            if not chosen_model:
                # Fall through to a known-good name; the call will 404 if it's
                # truly gone, and the OpenAI fallback picks up after that.
                chosen_model = "llama-3.1-8b-instant"

            logger.info(f"Using Groq model: {chosen_model} (available: {available_models[:5]})")

            response = await groq_client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=0.2,
            )
            text = response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("Groq chat failed, falling back to OpenAI: %s", e)
            last_error = e

    # Fallback to OpenAI if Groq failed or not configured
    if not text and get_openai_api_key():
        try:
            openai_client = get_openai_client()
            response = await openai_client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or ""
        except Exception as e:
            logger.exception("OpenAI chat failed")
            last_error = e

    if not text:
        raise HTTPException(status_code=502, detail="The assistant is unavailable. Please add credits to your AI provider account.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        # A reply that opens a fence but never closes it yields a single part;
        # indexing [1] used to raise IndexError and turn it into a 500.
        cleaned = parts[1] if len(parts) > 1 else parts[0]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    parsed = None
    if start != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
        except Exception:
            parsed = None

    if not isinstance(parsed, dict):
        return {"reply": _clean_str(text, MAX_REPLY_LEN), "actions": [], "transcript": transcript}

    return {
        "reply": _clean_str(parsed.get("reply"), MAX_REPLY_LEN),
        "actions": sanitize_actions(parsed.get("actions")),
        "transcript": transcript,
    }

# Include the router in the main app
app.include_router(api_router)

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "exp://localhost:8081",
    "exp://127.0.0.1:8081",
]

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if not allowed_origins:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
