from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Header, Depends
from starlette.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
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
import uuid
from datetime import datetime, timezone


# Configured before anything else so import-time failures below are logged
# rather than raising NameError on `logger`.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Supabase issues and signs the app's session tokens, so this server verifies
# them rather than minting its own. The anon key is public by design — it is
# sent as the `apikey` header Supabase's auth API requires, not as a secret.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    client.close()


app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)

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

@api_router.get("/")
async def root():
    return {"message": "Hello World"}


# ---------------------------------------------------------------------------
# Voice Assistant: Whisper transcription + LLM intent parsing
# ---------------------------------------------------------------------------
ALLOWED_AUDIO_EXT = {".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".wav", ".webm"}

_openai_client: Optional[AsyncOpenAI] = None


def get_llm_api_key() -> str:
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("EMERGENT_LLM_KEY")
        or ""
    )
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY or LLM_API_KEY is not configured")
    return api_key


def get_openai_client() -> AsyncOpenAI:
    """Built on first use and reused. A fresh AsyncOpenAI per request stands up a
    new httpx connection pool every time and throws away connection reuse; it is
    built lazily so an unconfigured key fails the request, not module import."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=get_llm_api_key())
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

    try:
        # Handed to the SDK as an in-memory (filename, bytes) pair. The previous
        # version spooled it to a NamedTemporaryFile, which blocked the event
        # loop on every read/write and leaked the file whenever the write itself
        # failed (the cleanup path only knew the name after a successful write).
        openai_client = get_openai_client()
        result = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=(f"recording{suffix}", audio),
            prompt="Hindi and English (Hinglish) shopkeeper ledger speech. Preserve names, numbers and rupee amounts.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("transcription failed")
        raise HTTPException(status_code=502, detail="Could not transcribe the recording. Please try again.")

    return {"text": getattr(result, "text", "") or ""}


@api_router.post("/voice/speak")
async def voice_speak(payload: SpeakRequest, user: dict = Depends(get_authenticated_user)):
    """Synthesize text to speech and stream the MP3 back.

    Returns the audio as a streaming response so the client can play() while
    bytes are still arriving. If TTS fails for any reason, the assistant's
    on-screen text reply still works — speech is a progressive enhancement.
    """
    enforce_user_rate_limit(str(user["user_id"]))

    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    # Cap at 2000 chars — OpenAI's hard limit is 4096 but shopkeeper replies
    # rarely exceed a couple of sentences; 2000 keeps cost bounded.
    text = text[:2000]

    # gpt-4o-mini-tts reads Hinglish cleanly with alloy. A separate Hindi voice
    # is unnecessary and adds complexity.
    model = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
    voice = "alloy"

    try:
        openai_client = get_openai_client()
        response = await openai_client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        )
        return StreamingResponse(
            response.iter_bytes(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("TTS failed")
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

    try:
        openai_client = get_openai_client()

        messages: List[Dict[str, str]] = [{"role": "system", "content": VOICE_SYSTEM_PROMPT}]
        # Include last 6 conversation turns so the model can ask clarifying questions.
        for turn in payload.history[-6:]:
            messages.append({"role": "user", "content": turn.get("user", "")})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": user_text})

        response = await openai_client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
    except HTTPException:
        raise
    except Exception:
        logger.exception("voice assist failed")
        raise HTTPException(status_code=502, detail="The assistant is unavailable right now. Please try again.")

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

# Authenticated and rate limited: these were open to the internet, so anyone
# could write unbounded documents into the database and read back every entry.
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate, user: dict = Depends(get_authenticated_user)):
    enforce_user_rate_limit(str(user["user_id"]))
    status_obj = StatusCheck(client_name=input.client_name)
    _ = await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks(user: dict = Depends(get_authenticated_user)):
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

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
