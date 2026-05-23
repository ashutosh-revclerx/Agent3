"""
main.py
───────
AI Consulting Copilot — FastAPI Backend
All routes delegate to the appropriate agent.

Multi-Agent Architecture:
  Agent 1 → facilitator          (phase transitions, messaging)
  Agent 2 → insight_mining       (Phase 2 objective map, Phase 3 clustering)
  Agent 3 → prompt_coaching      (Activity C scoring + simulation)
  Agent 4 → poll_consensus       (Phase 5 & 7 voting, consensus detection)
  Agent 5 → industry_benchmark   (Phase 6 adoption data)
  Agent 6 → prioritisation_roi   (Phase 8 impact/effort matrix)
  Agent 7 → deck_builder         (Phase 11 deliverables)

Database: PostgreSQL (async via asyncpg)
Redis: Deferred to later stages
"""
import uuid, random, string, datetime, json, asyncio, os, logging, base64
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import httpx
import websockets
from urllib.parse import quote
from env_loader import load_env

load_env()

# ── Database and agents ────────────────────────────────────────────────────────
import db
import redis_client
from agents import facilitator
from agents import insight_mining
from agents import prompt_coaching
from agents import poll_consensus
from agents import industry_benchmark
from agents import prioritisation_roi
from agents import deck_builder
from agents import opportunity_generation
from agents import scraping_agent
from agents import survey_agent
from seed_context import seed_session, build_system_prompt, get_department_names, BUSINESS_CONTEXT
from schemas import CompanyDNA, ParticipantProfile

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Lifespan Management
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init_db()
    logger.info("✅ Database connection pool initialized")
    await redis_client.init_redis()
    logger.info("✅ Redis client initialized")
    yield
    # Shutdown
    await redis_client.close_redis()
    logger.info("✅ Redis client closed")
    await db.close_db()
    logger.info("✅ Database connection pool closed")

app = FastAPI(
    title="AI Consulting Copilot",
    version="2.0.0",
    lifespan=lifespan
)
logger = logging.getLogger("copilot.tts")

app.add_middleware(
    CORSMiddleware,
    # Dev-friendly: always emit CORS headers so browser errors don't hide server errors.
    # If you need to lock this down later, replace with explicit origins.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Stores (session context cache, not persistent)
# ─────────────────────────────────────────────────────────────────────────────
sessions:      dict = {}   # code → session context (used for agent logic, persisted to DB)
participants:  dict = {}   # id   → participant context (used for agent logic, persisted to DB)
phase_data:    dict = {}   # code → { phase_key: [submissions] } (queried from DB)
ws_connections:dict = {}   # code → [WebSocket] (real-time broadcasts)
liveavatar_runtime: dict = {}  # session_id -> {websocket_url, agent_token, voice_id, mode}
liveavatar_speak_locks: dict = {}  # session_id -> asyncio.Lock for serialized audio pushes


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def generate_code(n=6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

def normalize_uuid(value: Optional[str]) -> Optional[str]:
    """Return canonical UUID string when valid; otherwise None."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except (ValueError, TypeError, AttributeError):
        return None

def upstream_error_text(resp: httpx.Response, max_len: int = 2000) -> str:
    """Return a compact upstream error payload safe for logs/client diagnostics."""
    text = (resp.text or "").strip()
    if not text:
        return "<empty body>"
    if len(text) > max_len:
        return f"{text[:max_len]}... [truncated]"
    return text

async def synthesize_pcm_24khz(text: str, voice_id: str, model_id: str = "eleven_turbo_v2") -> bytes:
    """Synthesize speech as raw PCM 16-bit 24kHz bytes via ElevenLabs."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "ELEVENLABS_API_KEY not set — cannot synthesize avatar speech.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=pcm_24000"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/pcm",
    }
    payload = {
        "text": text[:1500],
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        logger.error("ElevenLabs PCM request failed: %s", exc)
        raise HTTPException(502, "Could not synthesize avatar speech right now.")

    if resp.status_code >= 400:
        details = upstream_error_text(resp)
        logger.error("ElevenLabs PCM error %s: %s", resp.status_code, details)
        raise HTTPException(502, f"ElevenLabs speech error {resp.status_code}: {details}")

    content_type = (resp.headers.get("content-type", "") or "").lower()
    if "audio/pcm" not in content_type:
        logger.error("ElevenLabs returned non-PCM audio: content-type=%s", content_type or "<missing>")
        raise HTTPException(
            502,
            f"ElevenLabs returned '{content_type or 'unknown'}' instead of audio/pcm.",
        )

    audio_bytes = resp.content or b""
    if len(audio_bytes) < 512:
        raise HTTPException(502, "ElevenLabs returned empty PCM audio.")
    return audio_bytes

async def send_pcm_to_liveavatar_ws(
    websocket_url: str,
    agent_token: Optional[str],
    pcm_audio: bytes,
    event_id: str,
) -> None:
    """Push PCM chunks into LiveAvatar LITE websocket via agent.speak events."""
    headers = {}
    if agent_token:
        headers["Authorization"] = f"Bearer {agent_token}"

    async with websockets.connect(
        websocket_url,
        additional_headers=headers,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
        max_size=2_000_000,
    ) as ws:
        # Wait briefly for connected state; proceed anyway if no state event is emitted.
        try:
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw) if isinstance(raw, str) else {}
                if msg.get("type") == "session.state_updated" and msg.get("state") == "connected":
                    break
        except Exception:
            pass

        chunk_size = 9_600  # ~200ms @ 24kHz 16-bit mono (smoother realtime delivery)
        for i in range(0, len(pcm_audio), chunk_size):
            chunk = pcm_audio[i:i + chunk_size]
            payload = {
                "type": "agent.speak",
                "event_id": event_id,
                "audio": base64.b64encode(chunk).decode("ascii"),
            }
            await ws.send(json.dumps(payload))

        await ws.send(json.dumps({"type": "agent.speak_end", "event_id": event_id}))

async def push_text_to_liveavatar(
    session_id: str,
    text: str,
    voice_id: Optional[str] = None,
    model_id: str = "eleven_turbo_v2",
) -> str:
    runtime = liveavatar_runtime.get(session_id)
    if not runtime:
        raise HTTPException(404, "LiveAvatar session runtime not found. Start /liveavatar/embed first.")
    if runtime.get("mode") != "LITE":
        raise HTTPException(400, "liveavatar/speak is only supported for LITE mode sessions.")
    if not text.strip():
        raise HTTPException(400, "text is required")

    selected_voice = (
        voice_id
        or os.getenv("ELEVENLABS_VOICE_ID", "").strip()
        or runtime.get("voice_id")
        or "EXAVITQu4vr4xnSDxMaL"
    )
    pcm_audio = await synthesize_pcm_24khz(text.strip(), selected_voice, model_id=model_id)
    event_id = str(uuid.uuid4())
    lock = liveavatar_speak_locks.setdefault(session_id, asyncio.Lock())
    async with lock:
        last_exc = None
        for attempt in range(2):
            try:
                await send_pcm_to_liveavatar_ws(
                    websocket_url=runtime["websocket_url"],
                    agent_token=runtime.get("agent_token"),
                    pcm_audio=pcm_audio,
                    event_id=event_id,
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt == 0:
                    await asyncio.sleep(0.25)
                else:
                    raise
        if last_exc:
            raise last_exc
    return event_id

def generate_liveavatar_reply(
    user_text: str,
    participant_name: Optional[str] = None,
    participant_role: Optional[str] = None,
    company_name: Optional[str] = None,
    host_location: Optional[str] = None,
    host_fun_fact: Optional[str] = None,
    conversation: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Generate a concise conversational reply for avatar playback."""
    from gemini_client import gemini_text

    conversation = conversation or []
    recent_turns = conversation[-8:]
    convo_lines = []
    for turn in recent_turns:
        role = (turn.get("role") or "").strip().lower()
        text = (turn.get("text") or "").strip()
        if role in {"user", "assistant"} and text:
            convo_lines.append(f"{role}: {text}")

    prompt = (
        "You are a warm onboarding AI assistant speaking through a live avatar.\n"
        "Reply naturally to the user in 1-2 concise sentences.\n"
        "Do not use markdown, bullets, labels, or stage directions.\n"
        "If the user asks for help, ask one clear follow-up question.\n\n"
        f"Participant name: {participant_name or 'there'}\n"
        f"Participant role: {participant_role or 'participant'}\n"
        f"Company: {company_name or 'their company'}\n"
        f"Location context: {host_location or 'not provided'}\n"
        f"Fun fact context: {host_fun_fact or 'not provided'}\n"
        f"Recent context:\n" + ("\n".join(convo_lines) if convo_lines else "(none)") + "\n\n"
        f"User message: {user_text.strip()}\n\n"
        "Return only what should be spoken aloud."
    )
    reply = gemini_text(prompt)
    if reply and reply.strip():
        return reply.strip()
    return "Thanks for sharing that. Could you tell me a bit more so I can help better?"

def build_host_context(
    host_name: str,
    company: str,
    host_location: Optional[str],
) -> Dict[str, Any]:
    """
    Build host context for avatar personalization.
    - Uses OpenWeather + Gemini web search via scraping_agent.get_weather_and_sports
    - Generates fun fact with Gemini when one is not manually provided
    """
    location = (host_location or "").strip()
    local_context: Dict[str, Any] = {}
    generated_fun_fact = ""

    if location:
        try:
            local_context = scraping_agent.get_weather_and_sports(location) or {}
        except Exception as exc:
            logger.warning("Host context weather/sports lookup failed for %s: %s", location, exc)
        local_context["location"] = location

    try:
        from gemini_client import gemini_text, gemini_json_with_web_search

        web_hint = {}
        if location:
            web_hint = gemini_json_with_web_search(
                f"Find one current, professional small-talk nugget for {location}. "
                f"Return JSON only: {{\"local_icebreaker\": \"...\"}}"
            ) or {}

        prompt = (
            "Create one short fun fact for workshop conversation context.\n"
            "Keep it professional, neutral, and conversational (max 20 words).\n"
            "Return only the fun fact sentence.\n\n"
            f"Host name: {host_name}\n"
            f"Company: {company}\n"
            f"Location: {location or 'not provided'}\n"
            f"Local context: {json.dumps(local_context) if local_context else 'not available'}\n"
            f"Web hint: {json.dumps(web_hint) if web_hint else 'not available'}\n"
        )
        generated_fun_fact = (gemini_text(prompt) or "").strip()
    except Exception as exc:
        logger.warning("Host fun fact generation failed: %s", exc)

    if not generated_fun_fact:
        generated_fun_fact = (
            local_context.get("sports_icebreaker")
            or local_context.get("weather")
            or ""
        )

    return {
        "host_location": location or None,
        "host_fun_fact": generated_fun_fact or None,
        "host_local_context": local_context or {},
    }


def generate_dynamic_fun_fact(
    location: Optional[str],
    participant_role: Optional[str],
    company_name: Optional[str],
    base_fun_fact: Optional[str] = None,
) -> str:
    """
    Generate a fresh, random fun fact for the current participant interaction.
    Prioritizes:
    1) Location-aware small talk
    2) Role-relevant tech/news angle
    3) Mixed blend
    """
    loc = (location or "").strip()
    role = (participant_role or "business professional").strip()
    company = (company_name or "the company").strip()
    fallback = (base_fun_fact or "").strip()

    try:
        from gemini_client import gemini_text, gemini_json_with_web_search

        theme = random.choice(["location", "role_tech", "mixed"])
        hints: Dict[str, Any] = {}

        if loc:
            location_hint = gemini_json_with_web_search(
                f"Find one current, neutral local highlight for {loc}. "
                f"Return JSON only: {{\"location_highlight\":\"...\"}}"
            ) or {}
            if isinstance(location_hint, dict):
                hints.update(location_hint)

        role_hint = gemini_json_with_web_search(
            f"Find one current tech trend or headline relevant to a {role}. "
            f"Return JSON only: {{\"role_tech_highlight\":\"...\"}}"
        ) or {}
        if isinstance(role_hint, dict):
            hints.update(role_hint)

        prompt = (
            "Write ONE short fun fact for a live onboarding conversation.\n"
            "Rules:\n"
            "- 1 sentence only, max 18 words.\n"
            "- Professional, friendly, and easy to say aloud.\n"
            "- No hype, no emojis, no bullet points.\n"
            f"- Theme to prioritize: {theme}.\n\n"
            f"Participant role: {role}\n"
            f"Company: {company}\n"
            f"Location: {loc or 'not provided'}\n"
            f"Hints: {json.dumps(hints) if hints else 'none'}\n"
            f"Fallback context: {fallback or 'none'}\n\n"
            "Return only the fun fact sentence."
        )
        fact = (gemini_text(prompt) or "").strip()
        if fact:
            return fact
    except Exception as exc:
        logger.warning("Dynamic fun fact generation failed: %s", exc)

    return fallback

def store(session_code: str, key: str, value: dict):
    """Append a submission to a phase data bucket."""
    if session_code not in phase_data:
        phase_data[session_code] = {}
    if key not in phase_data[session_code]:
        phase_data[session_code][key] = []
    phase_data[session_code][key].append(value)

def get_store(session_code: str, key: str) -> list:
    return phase_data.get(session_code, {}).get(key, [])

async def broadcast(code: str, message: dict):
    conns = ws_connections.get(code, [])
    dead  = []
    for ws in conns:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.append(ws)
    for ws in dead:
        conns.remove(ws)


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────
class CreateSessionRequest(BaseModel):
    host_name: str;  company: str;  industry: str
    participant_count: int = 0;  duration_mins: int = 90
    company_url: Optional[str] = None # Added for website scraping
    company_linkedin_url: Optional[str] = None
    host_location: Optional[str] = None
    host_fun_fact: Optional[str] = None
    avatar_id: Optional[str] = None  # LiveAvatar avatar ID
    voice_id: Optional[str] = None   # ElevenLabs voice ID
    liveavatar_video_quality: Optional[str] = None
    liveavatar_video_encoding: Optional[str] = None

class JoinRequest(BaseModel):
    session_code: str;  name: str;  role: str
    department: str;  top_challenge: str;  ai_confidence: int
    daily_work: str = ""
    conversation: list = []  # full onboarding chat transcript [{role, text}]
    workflow_summary: str = ""  # pre-summarised by client (optional)
    linkedin_url: Optional[str] = None # Added for LinkedIn scraping

class Phase2Request(BaseModel):
    session_code:     str
    participant_id:   Optional[str] = None
    participant_role: str = "Other"
    objectives:       List[str]
    growth_areas:     List[str]
    challenges:       str

class ProblemItem(BaseModel):
    text: str
    tags: List[str] = Field(default_factory=list)
    severity: int = 3
    department: str = ""
    workflow_description: str = ""

class Phase3Request(BaseModel):
    session_code: str;  participant_id: Optional[str] = None
    problems: List[ProblemItem]

class Phase4Request(BaseModel):
    session_code: str

class DatasetScore(BaseModel):
    dataset: str;  label: str;  scores: dict;  readiness: float

class DataAuditRequest(BaseModel):
    session_code: str;  participant_id: Optional[str] = None
    datasets: List[DatasetScore]

class ConfidenceRequest(BaseModel):
    session_code: str;  participant_id: Optional[str] = None
    confidence_level: int;  concerns: List[str] = [];  expectations: str = ""

class ScenarioRequest(BaseModel):
    session_code:   str
    participant_id: Optional[str] = None
    role:           str = "Other"
    department:     str = ""

class PromptRequest(BaseModel):
    session_code:   str
    participant_id: Optional[str] = None
    prompt:         str
    task_context:   str = ""
    scenario_id:    Optional[str] = None
    scenario:       Optional[dict] = None

class SimulationRequest(BaseModel):
    session_code:   str
    participant_id: Optional[str] = None
    prompt:         str
    task_context:   str = ""
    scenario:       Optional[dict] = None

class VoteRequest(BaseModel):
    session_code: str;  participant_id: Optional[str] = None
    poll_number: int;   voted_ids: List[str]

class BenchmarkRequest(BaseModel):
    session_code: str

class RevealRequest(BaseModel):
    session_code: str;  phase: str


class LiveAvatarEmbedRequest(BaseModel):
    """Request to start a LiveAvatar session for the frontend.
    
    The backend owns session token generation + session start, then returns
    the WebRTC details the frontend needs.
    """
    session_code: Optional[str] = None
    participant_name: Optional[str] = None
    participant_role: Optional[str] = None
    linkedin_url: Optional[str] = None

class LiveAvatarKeepAliveRequest(BaseModel):
    session_id: str

class LiveAvatarStopRequest(BaseModel):
    session_id: str
    reason: str = "USER_CLOSED"

class LiveAvatarSpeakRequest(BaseModel):
    session_id: str
    text: str
    voice_id: Optional[str] = None
    model_id: str = "eleven_turbo_v2"

class LiveAvatarRespondRequest(BaseModel):
    session_id: str
    user_text: str
    session_code: Optional[str] = None
    participant_name: Optional[str] = None
    participant_role: Optional[str] = None
    conversation: List[Dict[str, str]] = Field(default_factory=list)
    voice_id: Optional[str] = None
    model_id: str = "eleven_turbo_v2"


# ─────────────────────────────────────────────────────────────────────────────
# Health & Root
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "AI Consulting Copilot v2 ✅", "agents": 7}

@app.get("/health")
def health():
    return {
        "status":       "healthy",
        "sessions":     len(sessions),
        "participants": len(participants),
        "gemini":       bool(os.getenv("GEMINI_API_KEY")),
        "timestamp":    datetime.datetime.utcnow().isoformat(),
    }


@app.post("/liveavatar/embed")
async def create_liveavatar_embed(req: LiveAvatarEmbedRequest):
    """
    Start a LiveAvatar session on the backend and return the session details.

    LITE mode lifecycle:
    1. Generate a LITE session token on the backend
    2. Start the session on the backend
    3. Pass WebRTC credentials to the frontend
    """
    api_key = os.getenv("LIVEAVATAR_API_KEY", "").strip()
    mode_env = os.getenv("LIVEAVATAR_MODE", "LITE").strip().upper()
    mode = mode_env if mode_env in {"FULL", "LITE"} else "FULL"
    code = (req.session_code or "").strip().upper()
    session = sessions.get(code) if code else None

    session_avatar_raw = (session or {}).get("avatar_id")
    env_avatar_raw = os.getenv("LIVEAVATAR_AVATAR_ID", "").strip()
    session_avatar_id = normalize_uuid(session_avatar_raw)
    env_avatar_id = normalize_uuid(env_avatar_raw)

    if session_avatar_raw and not session_avatar_id:
        logger.warning(
            "Session %s has invalid avatar_id '%s'; ignoring and trying env fallback",
            code or "<no-code>",
            session_avatar_raw,
        )
    if env_avatar_raw and not env_avatar_id:
        logger.error("LIVEAVATAR_AVATAR_ID is not a valid UUID: %s", env_avatar_raw)

    # Environment configuration must take precedence over session/request values.
    avatar_id = env_avatar_id or session_avatar_id
    sandbox = os.getenv("LIVEAVATAR_SANDBOX", "true").strip().lower() in {"1", "true", "yes", "on"}
    env_video_quality = os.getenv("LIVEAVATAR_VIDEO_QUALITY", "").strip()
    env_video_encoding = os.getenv("LIVEAVATAR_VIDEO_ENCODING", "").strip()
    video_quality = (
        env_video_quality
        or (session or {}).get("liveavatar_video_quality")
        or "high"
    )
    video_encoding = (
        env_video_encoding
        or (session or {}).get("liveavatar_video_encoding")
        or "VP8"
    )
    custom_livekit_url = os.getenv("LIVEAVATAR_CUSTOM_LIVEKIT_URL", "").strip()
    custom_livekit_token = os.getenv("LIVEAVATAR_CUSTOM_LIVEKIT_TOKEN", "").strip()
    context_id = os.getenv("LIVEAVATAR_CONTEXT_ID", "").strip()
    language = os.getenv("LIVEAVATAR_LANGUAGE", "en").strip() or "en"
    env_voice_id = os.getenv("LIVEAVATAR_VOICE_ID", "").strip()
    full_mode_voice_id = env_voice_id or (session or {}).get("voice_id") or "EXAVITQu4vr4xnSDxMaL"

    if not api_key:
        raise HTTPException(
            503,
            "LiveAvatar is not configured. Set LIVEAVATAR_API_KEY in backend/.env.",
        )

    if not avatar_id:
        raise HTTPException(
            400,
            "Invalid avatar_id. LiveAvatar requires a UUID avatar_id. "
            "Pass a valid UUID in session creation or set LIVEAVATAR_AVATAR_ID to a UUID.",
        )

    if mode == "FULL" and (not context_id or not full_mode_voice_id):
        raise HTTPException(
            503,
            "FULL mode requires LIVEAVATAR_CONTEXT_ID and LIVEAVATAR_VOICE_ID in backend/.env.",
        )

    from gemini_client import gemini_text

    prompt_name = (req.participant_name or "there").strip() or "there"
    prompt_role = (req.participant_role or "participant").strip() or "participant"
    linkedin_url = (req.linkedin_url or "").strip()
    host_location = ((session or {}).get("host_location") or "").strip()
    host_fun_fact = ((session or {}).get("host_fun_fact") or "").strip()
    dynamic_fun_fact = generate_dynamic_fun_fact(
        location=host_location,
        participant_role=prompt_role,
        company_name=(session or {}).get("company"),
        base_fun_fact=host_fun_fact,
    )
    greeting_prompt = (
        f"Write one short spoken opening line for a LiveAvatar onboarding assistant.\n"
        f"Participant name: {prompt_name}\n"
        f"Participant role: {prompt_role}\n"
        f"LinkedIn URL: {linkedin_url or 'not provided'}\n\n"
        f"Location context: {host_location or 'not provided'}\n"
        f"Fun fact context: {dynamic_fun_fact or host_fun_fact or 'not provided'}\n\n"
        f"Requirements:\n"
        f"- Warm, professional, and concise.\n"
        f"- Ask one first onboarding question after the greeting.\n"
        f"- Keep it to 1-2 sentences.\n"
        f"- Return only the line to be spoken."
    )
    opening_text = gemini_text(greeting_prompt) or (
        f"Hi {prompt_name}, welcome. I'm your onboarding avatar. What's the main challenge you'd like help with today?"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_payload = {
                "mode": mode,
                "avatar_id": avatar_id,
                "is_sandbox": sandbox,
                "video_settings": {
                    "quality": video_quality,
                    "encoding": video_encoding,
                },
            }

            if mode == "FULL":
                token_payload["avatar_persona"] = {
                    "voice_id": full_mode_voice_id,
                    "context_id": context_id,
                    "language": language,
                }

            # Optional: bring your own LiveKit infrastructure for LITE sessions.
            if mode == "LITE" and custom_livekit_url and custom_livekit_token:
                token_payload["livekit_config"] = {
                    "url": custom_livekit_url,
                    "token": custom_livekit_token,
                }

            token_resp = await client.post(
                "https://api.liveavatar.com/v1/sessions/token",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=token_payload,
            )
    except httpx.HTTPError as exc:
        logger.error("LiveAvatar token request failed: %s", exc)
        raise HTTPException(502, "Could not create a LiveAvatar session token right now.")

    if token_resp.status_code == 422:
        details = upstream_error_text(token_resp)
        logger.error("LiveAvatar token validation error 422: %s", details)
        raise HTTPException(400, f"LiveAvatar request validation failed: {details}")

    if token_resp.status_code >= 400:
        details = upstream_error_text(token_resp)
        logger.error("LiveAvatar token error %s: %s", token_resp.status_code, details)
        raise HTTPException(
            502,
            f"LiveAvatar token error {token_resp.status_code}: {details}",
        )

    token_data = token_resp.json()
    session_id = (
        token_data.get("session_id")
        or token_data.get("data", {}).get("session_id")
    )
    session_token = (
        token_data.get("session_token")
        or token_data.get("data", {}).get("session_token")
    )
    if not session_id or not session_token:
        logger.error("LiveAvatar token response missing session info: %s", token_data)
        raise HTTPException(502, "LiveAvatar did not return a session token.")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            start_resp = await client.post(
                "https://api.liveavatar.com/v1/sessions/start",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {session_token}",
                },
            )
    except httpx.HTTPError as exc:
        logger.error("LiveAvatar session start failed: %s", exc)
        raise HTTPException(502, "Could not start the LiveAvatar session right now.")

    if start_resp.status_code >= 400:
        details = upstream_error_text(start_resp)
        logger.error("LiveAvatar start error %s: %s", start_resp.status_code, details)
        raise HTTPException(
            502,
            f"LiveAvatar start error {start_resp.status_code}: {details}",
        )

    start_data = start_resp.json()
    start_data = start_data.get("data", start_data)
    livekit_url = start_data.get("livekit_url")
    livekit_token = start_data.get("livekit_client_token") or start_data.get("livekit_token")
    websocket_url = (
        start_data.get("websocket_url")
        or start_data.get("ws_url")
        or start_data.get("session_websocket_url")
    )
    agent_token = (
        start_data.get("agent_token")
        or start_data.get("livekit_agent_token")
    )
    if not livekit_url or not livekit_token:
        logger.error("LiveAvatar start response missing room info: %s", start_data)
        raise HTTPException(502, "LiveAvatar did not return LiveKit room credentials.")

    if session_id:
        liveavatar_runtime[session_id] = {
            "websocket_url": websocket_url,
            "agent_token": agent_token,
            "voice_id": full_mode_voice_id,
            "mode": mode,
            "host_location": host_location or None,
            "fun_fact": dynamic_fun_fact or host_fun_fact or None,
        }

    # In LITE mode, proactively send opening text so avatar greets immediately.
    if mode == "LITE" and session_id and websocket_url and opening_text.strip():
        async def _speak_opening_text():
            try:
                await push_text_to_liveavatar(session_id, opening_text)
            except Exception as exc:
                logger.warning("LiveAvatar opening speak failed for %s: %s", session_id, exc)
        asyncio.create_task(_speak_opening_text())

    embed_url = (
        f"https://meet.livekit.io/custom?liveKitUrl={quote(livekit_url, safe='')}"
        f"&token={quote(livekit_token, safe='')}"
    )

    return {
        "embed_url": embed_url,
        "livekit_url": livekit_url,
        "livekit_token": livekit_token,
        "websocket_url": websocket_url,
        "agent_token": agent_token,
        "session_id": session_id,
        "session_token": session_token,
        "mode": mode,
        "sandbox": sandbox,
        "avatar_id": avatar_id,
        "video_settings": {
            "quality": video_quality,
            "encoding": video_encoding,
        },
        "opening_text": opening_text,
    }


@app.post("/liveavatar/keep-alive")
async def keep_liveavatar_session_alive(req: LiveAvatarKeepAliveRequest):
    """
    Keep a LiveAvatar session alive while the frontend is still connected.
    """
    api_key = os.getenv("LIVEAVATAR_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "LiveAvatar API key is not configured.")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.liveavatar.com/v1/sessions/keep-alive",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"session_id": req.session_id},
            )
    except httpx.HTTPError as exc:
        logger.error("LiveAvatar keep-alive request failed: %s", exc)
        raise HTTPException(502, "Could not keep the LiveAvatar session alive.")

    if resp.status_code >= 400:
        details = upstream_error_text(resp)
        logger.error("LiveAvatar keep-alive error %s: %s", resp.status_code, details)
        raise HTTPException(
            502,
            f"LiveAvatar keep-alive error {resp.status_code}: {details}",
        )

    return resp.json()


@app.post("/liveavatar/stop")
async def stop_liveavatar_session(req: LiveAvatarStopRequest):
    """
    Stop the LiveAvatar session when the user exits the onboarding avatar step.
    """
    api_key = os.getenv("LIVEAVATAR_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "LiveAvatar API key is not configured.")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.liveavatar.com/v1/sessions/stop",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "session_id": req.session_id,
                    "reason": req.reason or "USER_CLOSED",
                },
            )
    except httpx.HTTPError as exc:
        logger.error("LiveAvatar stop request failed: %s", exc)
        raise HTTPException(502, "Could not stop the LiveAvatar session.")

    if resp.status_code >= 400:
        details = upstream_error_text(resp)
        logger.error("LiveAvatar stop error %s: %s", resp.status_code, details)
        raise HTTPException(
            502,
            f"LiveAvatar stop error {resp.status_code}: {details}",
        )

    liveavatar_runtime.pop(req.session_id, None)
    liveavatar_speak_locks.pop(req.session_id, None)
    return resp.json()


@app.post("/liveavatar/speak")
async def liveavatar_speak(req: LiveAvatarSpeakRequest):
    """
    LITE mode helper: convert text to ElevenLabs PCM and stream it to the avatar websocket.
    """
    try:
        event_id = await push_text_to_liveavatar(
            session_id=req.session_id,
            text=req.text,
            voice_id=req.voice_id,
            model_id=req.model_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("liveavatar/speak failed for %s: %s", req.session_id, exc)
        raise HTTPException(502, f"LiveAvatar speak pipeline failed: {type(exc).__name__}: {exc}")
    return {
        "status": "ok",
        "session_id": req.session_id,
        "event_id": event_id,
    }


@app.post("/liveavatar/respond")
async def liveavatar_respond(req: LiveAvatarRespondRequest):
    """
    End-to-end LITE turn:
    1) Generate LLM text reply
    2) Synthesize via ElevenLabs (PCM)
    3) Push audio to LiveAvatar websocket for avatar speech
    """
    user_text = (req.user_text or "").strip()
    if not user_text:
        raise HTTPException(400, "user_text is required")

    code = (req.session_code or "").strip().upper()
    session = sessions.get(code) if code else {}
    runtime = liveavatar_runtime.get(req.session_id) or {}
    company_name = session.get("company") if session else None
    host_location = runtime.get("host_location") or (session.get("host_location") if session else None)
    host_fun_fact = runtime.get("fun_fact") or (session.get("host_fun_fact") if session else None)

    assistant_text = generate_liveavatar_reply(
        user_text=user_text,
        participant_name=req.participant_name,
        participant_role=req.participant_role,
        company_name=company_name,
        host_location=host_location,
        host_fun_fact=host_fun_fact,
        conversation=req.conversation,
    )

    try:
        event_id = await push_text_to_liveavatar(
            session_id=req.session_id,
            text=assistant_text,
            voice_id=req.voice_id,
            model_id=req.model_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("liveavatar/respond failed for %s: %s", req.session_id, exc)
        raise HTTPException(502, f"LiveAvatar respond pipeline failed: {type(exc).__name__}: {exc}")

    return {
        "status": "ok",
        "session_id": req.session_id,
        "event_id": event_id,
        "assistant_text": assistant_text,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 0 — Session Setup
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/session/create")
async def create_session(req: CreateSessionRequest):
    code = generate_code()
    while code in sessions:
        code = generate_code()

    env_avatar_raw = os.getenv("LIVEAVATAR_AVATAR_ID", "").strip()
    env_avatar_id = normalize_uuid(env_avatar_raw)
    req_avatar_id = normalize_uuid(req.avatar_id)
    normalized_avatar_id = env_avatar_id or req_avatar_id

    if req.avatar_id and not req_avatar_id:
        logger.warning("Ignoring non-UUID avatar_id for new session %s: %s", code, req.avatar_id)
    if env_avatar_raw and not env_avatar_id:
        logger.error("LIVEAVATAR_AVATAR_ID is not a valid UUID: %s", env_avatar_raw)

    env_voice_id = os.getenv("LIVEAVATAR_VOICE_ID", "").strip()
    selected_voice_id = env_voice_id or req.voice_id
    env_video_quality = os.getenv("LIVEAVATAR_VIDEO_QUALITY", "").strip()
    env_video_encoding = os.getenv("LIVEAVATAR_VIDEO_ENCODING", "").strip()
    selected_video_quality = env_video_quality or req.liveavatar_video_quality or "high"
    selected_video_encoding = env_video_encoding or req.liveavatar_video_encoding or "VP8"
    host_context = build_host_context(
        host_name=req.host_name,
        company=req.company,
        host_location=req.host_location,
    )

    # Create session in database
    try:
        db_result = await db.create_session(
            code=code,
            host_name=req.host_name,
            company=req.company,
            industry=req.industry,
            participant_count=req.participant_count,
            duration_mins=req.duration_mins,
            avatar_id=normalized_avatar_id,
            voice_id=selected_voice_id,
        )
    except Exception as e:
        logger.exception("create_session: database insert failed")
        raise HTTPException(500, f"Database error creating session: {type(e).__name__}: {e}")

    # Build session context for agents (cached in memory)
    session = {
        "id": db_result["id"], "code": code,
        "host_name": req.host_name, "company": req.company,
        "industry": req.industry, "participant_count": req.participant_count,
        "duration_mins": req.duration_mins, "current_phase": 0,
        "company_url": req.company_url,
        "company_linkedin_url": req.company_linkedin_url,
        "host_location": host_context.get("host_location"),
        "host_fun_fact": host_context.get("host_fun_fact"),
        "host_local_context": host_context.get("host_local_context", {}),
        "avatar_id": normalized_avatar_id,  # LiveAvatar avatar selection
        "voice_id": selected_voice_id,    # Voice for app-managed TTS prompts
        "liveavatar_video_quality": selected_video_quality,
        "liveavatar_video_encoding": selected_video_encoding,
        "participants": [], "status": "waiting",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "revealed_phases": [],   # phases host has revealed to participants
        "team_confidence": None, # set by Activity B
        "workshop_data": {},     # accumulates all AI outputs
    }
    # Inject business entity seed context into all 7 agents
    session = seed_session(session)
    sessions[code] = session

    # Agent 5: pre-load industry benchmarks
    benchmarks = industry_benchmark.get_industry_benchmarks(req.industry)
    session["workshop_data"]["industry_benchmarks"] = benchmarks
    session["workshop_data"]["industry_benchmark_status"] = "idle"

    # Agent 1: generate phase 0 intro message (now seed-aware)
    intro = facilitator.get_phase_intro(0, req.company)
    logger.info(f"✅ Session created: {code} | {req.company} | {req.industry}")
    logger.info(f"   Avatar: {normalized_avatar_id} | Voice: {selected_voice_id}")
    logger.info(f"   Video: {session['liveavatar_video_quality']} | Encoding: {session['liveavatar_video_encoding']}")
    logger.info(f"   Host context: location={session.get('host_location')} | fun_fact={'yes' if session.get('host_fun_fact') else 'no'}")
    logger.info(f"   Seeded: {len(session['known_departments'])} departments, {len(session['pillar_names'])} pillars")

    # Start background company scraping if URL is provided
    if req.company_url:
        asyncio.create_task(background_company_scrape(code, req.company_url))
    if req.industry.strip():
        asyncio.create_task(background_industry_benchmark_prefetch(code))

    return {**session, "intro_message": intro}


async def background_company_scrape(session_code: str, url: str):
    """Background task using Scraping Agent. Stores to DB and broadcasts to participants."""
    try:
        dna_data = await scraping_agent.run_company_scrape(session_code, url)
        if dna_data:
            # Store in database (persistent)
            await db.store_company_dna(session_code, dna_data)
            
            # Cache in memory for agent logic
            sessions[session_code]["company_dna"] = dna_data
            
            # Broadcast the DNA to the host/participants
            await broadcast(session_code, {"type": "company_dna_ready", "dna": dna_data})
            logger.info(f"Broadcasting Company DNA for {session_code}")
    except Exception as e:
        logger.error(f"Scraping Agent: Company scrape failed for {session_code}: {e}")


async def background_industry_benchmark_prefetch(session_code: str):
    """Pre-fetch live industry benchmark data as soon as the host provides an industry."""
    try:
        session = sessions.get(session_code)
        if not session:
            return

        industry = (session.get("industry") or "").strip()
        company = (session.get("company") or "").strip()
        if not industry:
            return

        workshop_data = session.setdefault("workshop_data", {})
        workshop_data["industry_benchmark_status"] = "loading"

        enriched = await asyncio.to_thread(
            industry_benchmark.enrich_with_gemini,
            industry,
            company,
            [],
        )
        workshop_data["industry_benchmark_prefetch"] = enriched
        workshop_data["industry_benchmark_status"] = "ready"

        await broadcast(
            session_code,
            {"type": "industry_benchmark_prefetched", "data": enriched},
        )
        logger.info("Industry benchmark prefetched for %s (%s)", session_code, industry)
    except Exception as e:
        session = sessions.get(session_code)
        if session:
            session.setdefault("workshop_data", {})["industry_benchmark_status"] = "failed"
        logger.error("Industry benchmark prefetch failed for %s: %s", session_code, e)


@app.get("/session/{code}")
def get_session(code: str):
    code = code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, f"Session '{code}' not found in memory. It may have been lost during a server reload.")
    return sessions[code]

@app.get("/session/{code}/participants")
def get_participants(code: str):
    code = code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[code]
    return {"session_code": code, "count": len(s["participants"]),
            "participants": [participants[pid] for pid in s["participants"] if pid in participants]}



def summarise_onboarding_conversation(conversation: list, name: str, role: str, daily_work: str, top_challenge: str) -> str:
    """
    Summarises the full onboarding chat into a concise workflow description.
    Falls back to daily_work if Gemini is not available.
    """
    from gemini_client import gemini_text

    if not conversation:
        return daily_work  # nothing to summarise

    # Build a readable transcript
    lines = []
    for m in conversation:
        speaker = "Participant" if m.get("role") == "user" else "Facilitator"
        text = m.get("text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    transcript = "\n".join(lines)

    prompt = (
        f"You are summarising an onboarding conversation for an AI workshop participant.\n\n"
        f"Participant: {name} | Role: {role}\n\n"
        f"Conversation transcript:\n{transcript}\n\n"
        f"Write a clear, concise summary (3-5 sentences) of this person's day-to-day workflow "
        f"and the main challenge they described. "
        f"Focus on: what they do regularly, what tools or systems they use, and what slows them down. "
        f"Write in third person (e.g. '{name} spends...'). "
        f"Retain all specific details — tools, systems, time spent, pain points. "
        f"Do not add commentary or recommendations. Return only the summary paragraph."
    )

    summary = gemini_text(prompt)
    if summary and len(summary.strip()) > 30:
        return summary.strip()

    # Fallback: stitch the two raw answers together
    parts = []
    if daily_work:
        parts.append(daily_work)
    if top_challenge and top_challenge != daily_work:
        parts.append(top_challenge)
    return " ".join(parts) if parts else daily_work


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Participant Onboarding
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/participant/join")
async def join_participant(req: JoinRequest):
    code = req.session_code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, f"Session '{code}' not found in memory (re-join may be required).")
    
    p = {
        "id": str(uuid.uuid4()), "session_code": code,
        "name": req.name, "role": req.role, "department": req.department,
        "top_challenge": req.top_challenge, "daily_work": req.daily_work, "ai_confidence": req.ai_confidence,
        "conversation": req.conversation,
        "workflow_summary": summarise_onboarding_conversation(
            req.conversation, req.name, req.role, req.daily_work, req.top_challenge
        ),
        "joined_at": datetime.datetime.utcnow().isoformat(),
    }
    sessions[code]["participants"].append(p["id"])
    participants[p["id"]] = p
    
    logger.info(f"👤 {req.name} ({req.role}) → {code}")
    
    await broadcast(code, {
        "type": "participant_joined",
        "count": len(sessions[code]["participants"]),
        "name": req.name
    })

    # Start background LinkedIn scraping if URL is provided
    if req.linkedin_url:
        asyncio.create_task(background_linkedin_scrape(code, p["id"], req.linkedin_url))

    return p


async def background_linkedin_scrape(session_code: str, participant_id: str, url: str):
    """Background task using Scraping Agent. Stores to DB and broadcasts to participant."""
    try:
        profile_data = await scraping_agent.run_linkedin_scrape(participant_id, url)
        if profile_data:
            # Store in database (persistent, with confirmed fields only)
            await db.create_participant(session_code, profile_data)
            
            # Cache in memory for agent logic
            participants[participant_id]["linkedin_profile"] = profile_data
            
            # Broadcast to the participant (or session)
            await broadcast(session_code, {
                "type": "participant_profile_ready",
                "participant_id": participant_id,
                "profile": profile_data
            })
            logger.info(f"Broadcasting Participant Profile for {participant_id}")
        else:
            # Extraction failed or login wall detected — trigger self-entry form
            logger.warning(f"LinkedIn scrape failed for {participant_id} — trigger self-entry fallback")
            await broadcast(session_code, {
                "type": "profile_self_entry_required",
                "participant_id": participant_id,
                "message": "Please manually enter your professional details"
            })
    except Exception as e:
        logger.error(f"LinkedIn scrape failed: {e}")
        await broadcast(session_code, {
            "type": "profile_error",
            "participant_id": participant_id,
            "message": "Failed to scrape LinkedIn profile. Please enter details manually."
        })

@app.post("/session/{code}/dna")
async def save_company_dna(code: str, dna: CompanyDNA):
    code = code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    sessions[code]["company_dna"] = dna.model_dump()
    logger.info(f"Host confirmed DNA for {code}")
    return {"status": "saved"}

@app.post("/participant/{id}/profile")
async def save_participant_profile(id: str, profile: ParticipantProfile):
    if id not in participants: raise HTTPException(404, "Participant not found")
    participants[id]["linkedin_profile"] = profile.model_dump()
    participants[id]["name"] = profile.name
    participants[id]["role"] = profile.role
    logger.info(f"Participant confirmed profile for {id}")
    return {"status": "saved"}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 Extended — Survey Questions / Coverage Map  [Agent 1: Facilitator]
# ─────────────────────────────────────────────────────────────────────────────
class SurveyResponseRequest(BaseModel):
    session_code: str
    participant_id: Optional[str] = None
    question_key: str  # e.g., "company_goals", "company_ai_maturity", "it_landscape", "success_definition"
    response: str


@app.get("/phase/survey/{session_code}/{question_key}")
async def get_survey_question(session_code: str, question_key: str, participant_id: Optional[str] = None):
    """
    Dynamically generate a Phase 1 survey question using LLM.
    Question keys: company_goals, company_ai_maturity, it_landscape, success_definition
    """
    code = session_code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    
    s = sessions[code]
    company = s.get("company", "")
    industry = s.get("industry", "")
    
    question = None
    
    if question_key == "company_goals":
        objectives = [obj.get("objectives", []) for obj in get_store(code, "phase2")]
        flat_objectives = [o for obj_list in objectives for o in obj_list]
        question = facilitator.get_company_goals_checkup(company, flat_objectives)
    
    elif question_key == "company_ai_maturity":
        question = facilitator.get_company_ai_maturity_question(company, industry)
    
    elif question_key == "it_landscape":
        question = facilitator.get_it_landscape_question(company)
    
    elif question_key == "success_definition":
        # This is per-participant
        if participant_id and participant_id in participants:
            p = participants[participant_id]
            question = facilitator.get_success_definition_prompt(p.get("name", ""), p.get("role", ""), company)
        else:
            question = facilitator.get_success_definition_prompt("", "", company)
    
    else:
        raise HTTPException(400, f"Unknown question key: {question_key}")
    
    if not question:
        question = f"Tell us more about {question_key} at your organization."
    
    return {"question_key": question_key, "question": question}


@app.post("/phase/survey-response")
async def submit_survey_response(req: SurveyResponseRequest):
    """
    Captures Phase 1 survey responses and persists to phase_data.
    """
    code = req.session_code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    
    # Store response to phase_data
    store(code, "phase1_survey", {
        "participant_id": req.participant_id,
        "question_key": req.question_key,
        "response": req.response,
        "submitted_at": datetime.datetime.utcnow().isoformat(),
    })
    
    all_responses = get_store(code, "phase1_survey")
    s = sessions[code]
    
    # Aggregate responses and update session workshop_data
    survey_map = {}
    for resp in all_responses:
        qkey = resp.get("question_key", "")
        if qkey not in survey_map:
            survey_map[qkey] = []
        survey_map[qkey].append(resp)
    
    s["workshop_data"]["phase1_survey_responses"] = survey_map
    
    # Broadcast survey progress
    await broadcast(code, {
        "type": "survey_response_recorded",
        "question_key": req.question_key,
        "total_responses": len(all_responses),
    })
    
    logger.info(f"Survey response recorded: {code} | {req.question_key} | participant {req.participant_id}")
    
    return {
        "status": "recorded",
        "question_key": req.question_key,
        "total_responses": len(all_responses),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Business Context  [Agent 2: Insight Mining]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/phase/context")
async def submit_context(req: Phase2Request):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    store(code, "phase2", {
        "participant_id":   req.participant_id,
        "participant_role": req.participant_role,
        "objectives":       req.objectives,
        "growth_areas":     req.growth_areas,
        "challenges":       req.challenges,
    })
    await broadcast(code, {"type": "context_count", "count": len(get_store(code, "phase2"))})

    # Agent 2
    objective_map = insight_mining.build_objective_map(
        s["company"], s["industry"], req.objectives, req.growth_areas,
        req.challenges
    )
    s["workshop_data"]["objective_map"] = objective_map

    # Agent 1: phase intro for phase 3
    transition = facilitator.get_transition_message("Business Context", "Problem Discovery", s["company"])
    return {"objective_map": objective_map, "transition_message": transition}


# HOST: reveal Phase 2 results to participants
@app.post("/phase/reveal")
async def reveal_phase(req: RevealRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]
    if req.phase not in s["revealed_phases"]:
        s["revealed_phases"].append(req.phase)
    data = s["workshop_data"].get(req.phase.replace("-", "_"), {})
    await broadcast(code, {"type": "phase_revealed", "phase": req.phase, "data": data})
    return {"revealed": True, "phase": req.phase}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Problem Discovery  [Agent 2: Insight Mining]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/phase/problems")
async def submit_problems(req: Phase3Request):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    for p in req.problems:
        store(code, "phase3", {
            "participant_id":      req.participant_id,
            "text":                p.text,
            "tags":                p.tags,
            "severity":            p.severity,
            "department":          p.department,
            "workflow_description": p.workflow_description,
        })

    all_problems = get_store(code, "phase3")
    await broadcast(code, {"type": "problems_count", "count": len(all_problems)})

    # Agent 2: cluster
    clusters = insight_mining.cluster_problems(s["company"], s["industry"], all_problems)
    s["workshop_data"]["problem_clusters"] = clusters

    # Detect sector overlap
    themes = [c.get("theme", "") for c in clusters]
    validated = insight_mining.detect_sector_overlap(s["industry"], themes)

    await broadcast(code, {"type": "problem_clusters", "data": clusters})
    return {"clusters": clusters, "sector_validated_themes": validated, "all_problems": all_problems}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Opportunity Generation  [Agent 2 + web grounding + self-verify]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/phase/opportunities")
async def generate_opportunities(req: Phase4Request):
    code = req.session_code.upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[code]

    # Attach phase_data to session for opportunity agent to read
    s["phase_data"] = phase_data.get(code, {})

    result = opportunity_generation.generate_use_cases(s)
    use_cases = result["use_cases"]

    # Persist into workshop_data
    s["workshop_data"]["use_cases"]            = use_cases
    s["workshop_data"]["verification_summary"] = result["verification_summary"]
    s["workshop_data"]["search_evidence"]      = result["search_evidence"]
    s["workshop_data"]["generation_metadata"]  = result["generation_metadata"]

    await broadcast(code, {
        "type": "use_cases_ready",
        "count": len(use_cases),
        "metadata": result["generation_metadata"],
    })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Activity A — Data Audit
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/activity/data-audit")
async def submit_data_audit(req: DataAuditRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    datasets_out = []
    readiness_map = {}
    for ds in req.datasets:
        avg = (sum(ds.scores.values()) / max(len(ds.scores), 1) + 1) if ds.scores else ds.readiness
        avg = round(min(avg, 4.0), 1)
        datasets_out.append({"label": ds.label, "dataset": ds.dataset, "avg_score": avg})
        readiness_map[ds.dataset] = avg

    datasets_out.sort(key=lambda x: x["avg_score"], reverse=True)
    s["workshop_data"]["data_readiness"] = {"datasets": datasets_out, "readiness_map": readiness_map}

    high = [d["label"] for d in datasets_out if d["avg_score"] >= 3]
    low  = [d["label"] for d in datasets_out if d["avg_score"] < 2]
    summary = f"{len(high)} dataset(s) AI-ready; {len(low)} need improvement before AI deployment."
    recommendation = f"Prioritise AI pilots using {high[0] if high else 'your strongest dataset'} first."

    await broadcast(code, {"type": "data_audit_complete", "datasets": datasets_out})
    return {"datasets": datasets_out, "summary": summary, "recommendation": recommendation}


# ─────────────────────────────────────────────────────────────────────────────
# Activity B — AI Confidence
# ─────────────────────────────────────────────────────────────────────────────
TONE_MAP = {
    1: "Use plain language. Avoid jargon. Focus on business outcomes.",
    2: "Be supportive. Use analogies. Build confidence gently.",
    3: "Use standard AI terms. Be practical and specific.",
    4: "Discuss implementation tradeoffs at a practitioner level.",
    5: "Use precise ML/AI terminology. Focus on architecture and strategy.",
}

CONCERN_RESPONSES = {
    "jobs":       "AI handles tedious work — your team focuses on higher-value thinking.",
    "security":   "AI processing stays within your data boundaries. We flag external-data use cases.",
    "cost":       "We prioritise quick wins: high-impact, low-cost automations with fast ROI.",
    "accuracy":   "Every AI output includes human review checkpoints. AI recommends, humans decide.",
    "privacy":    "Each use case is mapped to your compliance requirements.",
    "complexity": "We start simple — complexity only where it adds clear value.",
    "trust":      "Change management is part of every roadmap. Adoption before implementation.",
    "quality":    "Data readiness is Activity A — use cases match your actual data quality.",
}

@app.post("/activity/confidence")
async def submit_confidence(req: ConfidenceRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    store(code, "activity_b", {
        "participant_id": req.participant_id,
        "confidence_level": req.confidence_level,
        "concerns": req.concerns, "expectations": req.expectations,
    })

    all_responses = get_store(code, "activity_b")
    total         = len(all_responses)
    distribution  = {}
    all_concerns  = []
    for r in all_responses:
        lv = r["confidence_level"]
        distribution[lv] = distribution.get(lv, 0) + 1
        all_concerns.extend(r["concerns"])

    avg_conf     = sum(r["confidence_level"] for r in all_responses) / total
    top_concerns = sorted(set(all_concerns), key=lambda c: all_concerns.count(c), reverse=True)[:3]

    team_profile = {
        "total": total, "distribution": distribution,
        "avg_confidence": round(avg_conf, 1),
        "top_concerns": top_concerns,
        "adapted_tone": TONE_MAP.get(round(avg_conf), TONE_MAP[3]),
        "concern_response": CONCERN_RESPONSES.get(top_concerns[0]) if top_concerns else None,
    }
    s["workshop_data"]["confidence_profile"] = team_profile
    s["team_confidence"] = team_profile

    await broadcast(code, {"type": "team_confidence_profile", "data": team_profile})
    return {"team_profile": team_profile}


# ─────────────────────────────────────────────────────────────────────────────
# Activity C — Prompt Engineering  [Agent 3: Prompt Coaching]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/activity/prompt-scenario")
async def generate_scenario(req: ScenarioRequest):
    """Activity C Step 0 — generate a role-specific scenario before the user writes their prompt."""
    code = req.session_code.upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[code]

    scenario = prompt_coaching.generate_scenario(
        role=req.role,
        department=req.department,
        company=s["company"],
        industry=s["industry"],
    )
    # Tag with role so simulation can use it later
    scenario["role"] = req.role
    return scenario


@app.post("/activity/prompt-engineering")
async def score_prompt(req: PromptRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s    = sessions[code]
    conf = s.get("team_confidence", {}).get("avg_confidence", 3)

    # scenario_id can be sent from frontend to fetch the cached scenario
    scenario = None
    if hasattr(req, 'scenario_id') and req.scenario_id:
        scenario = s.get("cached_scenarios", {}).get(req.scenario_id)

    result = prompt_coaching.score_and_improve(
        req.prompt, req.task_context,
        s["company"], s["industry"],
        confidence_level=round(conf),
        scenario=scenario,
    )
    store(code, "activity_c", {"participant_id": req.participant_id, "original": req.prompt, "result": result})
    return result


@app.post("/activity/prompt-simulation")
async def run_simulation(req: SimulationRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    result = prompt_coaching.run_simulation(
        req.prompt, req.task_context, s["company"], s["industry"],
        scenario=req.scenario,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 & 7 — Polls  [Agent 4: Poll and Consensus]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/phase/vote")
async def submit_vote(req: VoteRequest):
    code = req.session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s    = sessions[code]
    key  = f"poll_{req.poll_number}"

    store(code, key, {"participant_id": req.participant_id, "voted_ids": req.voted_ids})
    all_votes = get_store(code, key)
    use_cases = s["workshop_data"].get("use_cases", [])

    results  = poll_consensus.tally_votes(all_votes, use_cases)
    consensus = poll_consensus.detect_consensus(results)

    # Generate GenAI summary of the voting pattern
    insight = None
    if len(all_votes) >= 1:
        insight = poll_consensus.generate_consensus_insight(s["company"], results)
        consensus["ai_insight"] = insight

    # On Poll 2, compute vote shift
    shift = None
    if req.poll_number == 2:
        poll1 = s["workshop_data"].get("poll1_results", [])
        shift = poll_consensus.measure_vote_shift(poll1, results)
        s["workshop_data"]["poll2_results"] = results
        s["workshop_data"]["vote_shift"]    = shift
    else:
        s["workshop_data"]["poll1_results"] = results
        s["workshop_data"]["poll1_consensus"] = consensus
    await broadcast(code, {"type": f"poll_{req.poll_number}_update", "results": results, "consensus": consensus})
    return {"results": results, "consensus": consensus, "shift": shift}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Industry Benchmark  [Agent 5: Industry Benchmark]
# ─────────────────────────────────────────────────────────────────────────────
def build_benchmark_payload(session_code: str):
    """
    Calls industry_benchmark.enrich_with_gemini (Tavily + Gemini web grounding)
    and normalises the result for the frontend.
    New agent already returns industry_adoption_pct and avg_roi directly.
    """
    code = session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    # Return cached result if already generated this session
    if s["workshop_data"].get("benchmark"):
        return code, s["workshop_data"]["benchmark"]

    prefetched = s["workshop_data"].get("industry_benchmark_prefetch")
    raw_use_cases       = s["workshop_data"].get("use_cases", [])
    org_use_cases       = [uc.get("title", "") for uc in raw_use_cases]

    # Agent 5: Tavily search ? Gemini web grounding ? static fallback
    # Reuse the phase-0 prefetch only when there are no organisation use cases yet.
    if prefetched and not org_use_cases:
        enriched = prefetched
    else:
        enriched = industry_benchmark.enrich_with_gemini(s["industry"], s["company"], org_use_cases)
    validated_use_cases = industry_benchmark.cross_reference_org_use_cases(raw_use_cases, s["industry"])

    # Normalise adoption_rate to int (new agent already does this, belt+braces)
    try:
        adoption_rate = int(str(enriched.get("adoption_rate", 0)).replace("%", "").strip())
    except (ValueError, TypeError):
        adoption_rate = 0

    # Normalise top_use_cases — new agent returns industry_adoption_pct + avg_roi directly
    top_use_cases = []
    for uc in enriched.get("top_use_cases", []):
        try:
            pct = int(str(uc.get("industry_adoption_pct", uc.get("adoption", 0))).replace("%", "").strip())
        except (ValueError, TypeError):
            pct = 0
        top_use_cases.append({
            **uc,
            "industry_adoption_pct": pct,
            "avg_roi":   uc.get("avg_roi") or uc.get("roi"),
            "description": uc.get("description") or f"Complexity: {uc.get('complexity', 'Unknown')}",
        })

    payload = {
        **enriched,
        "adoption_rate":       adoption_rate,
        "top_use_cases":       top_use_cases,
        "validated_use_cases": validated_use_cases,
    }
    s["workshop_data"]["benchmark"] = payload
    return code, payload


@app.get("/phase/benchmark/{session_code}")
async def get_benchmark(session_code: str):
    code, payload = build_benchmark_payload(session_code)

    await broadcast(code, {"type": "benchmark_ready", "data": payload})
    await broadcast(code, {"type": "benchmark_reveal", "data": payload})
    return payload


@app.post("/phase/benchmark")
async def post_benchmark(req: BenchmarkRequest):
    code, payload = build_benchmark_payload(req.session_code)

    await broadcast(code, {"type": "benchmark_ready", "data": payload})
    await broadcast(code, {"type": "benchmark_reveal", "data": payload})
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Prioritisation  [Agent 6: Prioritisation and ROI]
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/phase/prioritise")
async def prioritise(session_code: str):
    code = session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s  = sessions[code]
    wd = s["workshop_data"]

    use_cases     = wd.get("use_cases", [])
    readiness_map = wd.get("data_readiness", {}).get("readiness_map", {})

    scored = prioritisation_roi.score_use_cases(use_cases, readiness_map, s["company"], s["industry"])
    matrix = prioritisation_roi.build_matrix(scored)
    roi_summary = prioritisation_roi.generate_roi_summary(s["company"], matrix)

    s["workshop_data"]["matrix"]     = matrix
    s["workshop_data"]["roi_summary"] = roi_summary

    await broadcast(code, {"type": "matrix_ready", "matrix": matrix, "roi_summary": roi_summary})
    return {"matrix": matrix, "roi_summary": roi_summary}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 10 — Roadmap  [Agent 7: Deck Builder]
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/phase/roadmap/{session_code}")
async def generate_roadmap(session_code: str):
    code = session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s  = sessions[code]
    wd = s["workshop_data"]

    matrix   = wd.get("matrix", {})
    qw       = matrix.get("quadrants", {}).get("quick_win", [])
    strategic= matrix.get("quadrants", {}).get("strategic", [])
    rs       = wd.get("readiness_score", {}).get("overall_score", 5.0)

    roadmap = deck_builder.generate_roadmap(s["company"], s["industry"], qw, strategic, rs)
    s["workshop_data"]["roadmap"] = roadmap

    await broadcast(code, {"type": "roadmap_ready", "data": roadmap})
    return roadmap


# ─────────────────────────────────────────────────────────────────────────────
# Phase 11 — Deliverables  [Agent 7: Deck Builder]
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/phase/deliverables/{session_code}")
async def generate_deliverables(session_code: str):
    code = session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    deck     = deck_builder.build_deck_content(s, s["workshop_data"])
    summary  = deck_builder.generate_executive_summary(s, s["workshop_data"])
    s["workshop_data"]["deck"]    = deck
    s["workshop_data"]["summary"] = summary

    return {"deck": deck, "executive_summary": summary, "status": "ready"}


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket — real-time event bus
# ─────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws/{session_code}")
async def websocket_endpoint(websocket: WebSocket, session_code: str):
    code = session_code.upper()
    await websocket.accept()
    if code not in ws_connections:
        ws_connections[code] = []
    ws_connections[code].append(websocket)
    print(f"🔌 WS: {code} — {len(ws_connections[code])} connected")
    try:
        while True:
            await asyncio.wait_for(websocket.receive_text(), timeout=30)
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        if code in ws_connections:
            try: ws_connections[code].remove(websocket)
            except ValueError: pass
        print(f"🔌 WS disconnected: {code}")


# ─────────────────────────────────────────────────────────────────────────────
# Seed Context — inspect what's pre-loaded for a session
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/session/{code}/seed")
def get_session_seed(code: str):
    """Returns the pre-loaded seed context for a session (for debugging)."""
    code = code.upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[code]
    return {
        "session_code":        code,
        "pillars":             s.get("pillar_names", []),
        "departments":         s.get("known_departments", []),
        "agents_seeded":       list(s.get("seed", {}).keys()),
        "pain_points_loaded":  len(s.get("seed", {}).get("insight_mining", {}).get("known_pain_points", [])),
        "ai_opps_loaded":      len(s.get("seed", {}).get("industry_benchmark", {}).get("seeded_opportunities", [])),
        "quick_win_candidates":s.get("seed", {}).get("prioritisation_roi", {}).get("quick_win_candidates", []),
    }

@app.get("/seed/overview")
def seed_overview():
    """Global overview of the business entity seed — no session needed."""
    from seed_context import get_all_departments, get_all_pain_points, get_all_ai_opportunities
    depts = get_all_departments()
    return {
        "entity":          BUSINESS_CONTEXT["entity"],
        "pillars":         [p["name"] for p in BUSINESS_CONTEXT["pillars"]],
        "departments":     [d["name"] for d in depts],
        "total_pain_points":    len(get_all_pain_points()),
        "total_ai_opportunities": len(get_all_ai_opportunities()),
        "structure": {
            pillar["name"]: {
                "purpose": pillar["purpose"],
                "departments": [
                    {"name": d["name"], "function": d["function"]}
                    for d in pillar["departments"]
                ]
            }
            for pillar in BUSINESS_CONTEXT["pillars"]
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Voice — ElevenLabs TTS + transcript cleaning
# ─────────────────────────────────────────────────────────────────────────────
class SpeakRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    text: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs "Sarah" — professional, warm
    model_id: str = "eleven_turbo_v2"

class CleanRequest(BaseModel):
    text: str

@app.post("/ai/speak")
async def speak(req: SpeakRequest):
    """
    Proxy text to ElevenLabs TTS and stream MP3 audio back to the frontend.
    Falls back gracefully if ELEVENLABS_API_KEY is not set.
    """
    from fastapi.responses import Response
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        # Surface a clear error so the frontend can skip TTS gracefully.
        logger.warning("TTS disabled: ELEVENLABS_API_KEY not set")
        raise HTTPException(503, "ELEVENLABS_API_KEY not set — voice disabled")
    env_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    selected_voice_id = env_voice_id or req.voice_id
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": req.text[:1000],  # cap at 1000 chars per call
        "model_id": req.model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    req_id = uuid.uuid4().hex[:8]
    logger.info(
        "TTS request %s: voice_id=%s model_id=%s text_len=%s",
        req_id,
        selected_voice_id,
        req.model_id,
        len(req.text or ""),
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except Exception as e:
        logger.exception("TTS request %s: upstream request failed: %s", req_id, e)
        raise HTTPException(502, "ElevenLabs TTS request failed") from e

    content_type = resp.headers.get("content-type", "")
    content_length = resp.headers.get("content-length", "unknown")
    logger.info(
        "TTS request %s: upstream status=%s content_type=%s content_length=%s",
        req_id,
        resp.status_code,
        content_type or "unknown",
        content_length,
    )

    if resp.status_code != 200:
        detail = resp.text.strip()
        logger.warning(
            "TTS request %s: upstream non-200 detail=%r",
            req_id,
            detail[:200],
        )
        if len(detail) > 200:
            detail = detail[:200].rstrip() + "..."
        raise HTTPException(
            502,
            detail or f"ElevenLabs TTS failed with status {resp.status_code}",
        )

    audio_bytes = resp.content
    logger.info("TTS request %s: audio_bytes=%s", req_id, len(audio_bytes) if audio_bytes else 0)
    if not audio_bytes or len(audio_bytes) < 512:
        logger.warning(
            "TTS request %s: empty or too-small audio response (bytes=%s)",
            req_id,
            len(audio_bytes) if audio_bytes else 0,
        )
        raise HTTPException(502, "ElevenLabs TTS returned an empty audio response")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/ai/clean-transcript")
async def clean_transcript(req: CleanRequest):
    """
    Takes a raw speech transcript and returns a cleaned version.
    Removes filler words, fixes broken sentences, preserves meaning.
    """
    from gemini_client import gemini_text
    if not req.text or len(req.text.strip()) < 20:
        return {"cleaned": req.text, "changed": False}

    prompt = (
        f"Clean up this speech transcript. Remove filler words (um, uh, like, basically, "
        f"kind of, sort of, you know). Fix sentence structure. Preserve all meaning and "
        f"specific details. Keep it in first person. Return only the cleaned text, nothing else.\n\n"
        f"Transcript: {req.text}"
    )
    cleaned = gemini_text(prompt)
    if cleaned and cleaned != req.text:
        return {"cleaned": cleaned, "changed": True}
    return {"cleaned": req.text, "changed": False}

class OnboardingMessage(BaseModel):
    type: str
    text: str

class OnboardingChatRequest(BaseModel):
    messages: List[OnboardingMessage]
    name: Optional[str] = None
    role: str
    department: str

@app.post("/ai/onboarding-chat")
async def onboarding_chat_endpoint(req: OnboardingChatRequest):
    from agents.facilitator import process_onboarding_chat
    
    return process_onboarding_chat(
        messages=req.messages,
        name=req.name,
        role=req.role,
        department=req.department
    )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 - Avatar-Guided Survey (Workshop Guide + Gemini)
# ─────────────────────────────────────────────────────────────────────────────

class SurveyTurnRequest(BaseModel):
    """Request for next survey question and extraction."""
    session_code: str
    participant_id: Optional[str] = None
    turn: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current turn data: area, participant_response, response_word_count"
    )
    working_memory: Dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated state: confirmed_name, coverage_map, extracted_so_far, etc."
    )

class SurveyPersistRequest(BaseModel):
    """Request to persist survey data to phase_data table."""
    session_code: str
    participant_id: str
    extracted: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted data from survey: ai_maturity, company_ai_maturity, etc."
    )
    turn_history: List[Dict] = Field(
        default_factory=list,
        description="Full conversation history for audit trail"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Survey Agent: Question Generation & Data Extraction
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/agent/survey-turn")
async def survey_turn(req: SurveyTurnRequest):
    """
    Gemini survey agent: generates next question + extracts data from current response.
    
    Implements guided survey coverage + vocabulary calibration + pace adaptation.
    """
    code = req.session_code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[code]
    company_name = session.get("company", "")
    
    working_memory = req.working_memory or {}
    turn = req.turn or {}
    
    # Initialize coverage map if not present
    if "coverage_map" not in working_memory:
        working_memory["coverage_map"] = survey_agent.initialize_coverage_map()

    # Hydrate company DNA context from session when available.
    company_dna = session.get("company_dna") or {}
    if isinstance(company_dna, dict):
        if not working_memory.get("company_vision"):
            working_memory["company_vision"] = company_dna.get("vision", "")
        if not working_memory.get("company_goals"):
            working_memory["company_goals"] = company_dna.get("goals", [])

    # Hydrate participant role context so questions can be role-aware.
    if not working_memory.get("confirmed_role") and req.participant_id:
        participant_ctx = participants.get(req.participant_id) or {}
        if participant_ctx.get("role"):
            working_memory["confirmed_role"] = participant_ctx.get("role")
    
    # Turn history for pace calibration
    turn_history = working_memory.get("turn_history", [])
    
    # Step 1: Extract data from current response (if this is not the first turn)
    extracted_this_turn = {}
    current_area = turn.get("area")
    participant_response = turn.get("participant_response", "").strip()
    
    if current_area and participant_response:
        try:
            extracted_this_turn = await survey_agent.extract_data_from_response(
                current_area,
                participant_response,
                working_memory.get("extracted_so_far", {}).get("ai_maturity")
            )
            # Accumulate extracted data
            if extracted_this_turn:
                working_memory.setdefault("extracted_so_far", {}).update(extracted_this_turn)
        except Exception as exc:
            logger.error(f"Extraction failed for {current_area}: {exc}")
    
    # Step 2: Mark current area as answered
    if current_area and current_area in working_memory["coverage_map"]:
        working_memory["coverage_map"][current_area] = "answered"
    
    # Step 3: Check if session is complete
    if survey_agent.is_session_complete(working_memory["coverage_map"]):
        return {
            "next_question": "",
            "next_area": None,
            "extracted": extracted_this_turn,
            "coverage_map": working_memory["coverage_map"],
            "session_complete": True,
            "extracted_so_far": working_memory.get("extracted_so_far", {})
        }
    
    # Step 4: Get next area to cover
    next_area = survey_agent.get_next_area_to_cover(
        working_memory["coverage_map"],
        current_area
    )
    
    if not next_area:
        return {
            "next_question": "",
            "next_area": None,
            "extracted": extracted_this_turn,
            "coverage_map": working_memory["coverage_map"],
            "session_complete": True,
            "extracted_so_far": working_memory.get("extracted_so_far", {})
        }
    
    # Step 5: Generate next question
    try:
        ai_maturity = working_memory.get("extracted_so_far", {}).get("ai_maturity")
        response_word_count = survey_agent.get_average_response_length(turn_history)

        next_question = await survey_agent.generate_question_for_area(
            next_area,
            working_memory.get("confirmed_name", ""),
            company_name,
            ai_maturity,
            response_word_count,
            context={
                "company_vision": working_memory.get("company_vision", ""),
                "company_goals": working_memory.get("company_goals", []),
                "industry": session.get("industry", ""),
                "participant_role": working_memory.get("confirmed_role", ""),
            },
        )
    except Exception as exc:
        logger.error(f"Question generation failed for {next_area}: {exc}")
        next_question = f"Tell me more about { next_area.replace('_', ' ')}."
    
    # Mark next area as asked
    working_memory["coverage_map"][next_area] = "asked"
    
    # Update turn history
    if current_area:
        turn_history.append({
            "area": current_area,
            "participant_response": participant_response,
            "extracted": extracted_this_turn
        })
    working_memory["turn_history"] = turn_history
    
    return {
        "next_question": next_question,
        "next_area": next_area,
        "extracted": extracted_this_turn,
        "coverage_map": working_memory["coverage_map"],
        "session_complete": False,
        "extracted_so_far": working_memory.get("extracted_so_far", {})
    }


@app.post("/survey/persist")
async def persist_survey_data(req: SurveyPersistRequest):
    """
    Write survey results to phase_data table.
    One row per area with extracted data.
    """
    code = req.session_code.strip().upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    
    session = sessions[code]
    session_id = session.get("id")
    participant_id = req.participant_id
    extracted = req.extracted or {}
    
    try:
        # Write one phase_data row per area with data
        for area_key, value in extracted.items():
            if not value:
                continue
            
            # Store in phase_data table
            store(code, "phase1_avatar_survey", {
                "participant_id": participant_id,
                "area": area_key,
                "value": value,
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
        
        # Broadcast to participants
        await broadcast(code, {
            "type": "survey_complete",
            "participant_id": participant_id,
            "areas_captured": len([v for v in extracted.values() if v])
        })
        
        logger.info(f"Survey data persisted for {participant_id} in {code}")
        
        return {
            "status": "persisted",
            "participant_id": participant_id,
            "areas_captured": len([v for v in extracted.values() if v])
        }
    except Exception as exc:
        logger.error(f"Survey persistence failed: {exc}")
        raise HTTPException(500, f"Failed to persist survey data: {exc}")

