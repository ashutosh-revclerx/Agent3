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
import uuid, random, string, datetime, json, asyncio, os, logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
from env_loader import load_env

load_env()

# ── Database and agents ────────────────────────────────────────────────────────
import db
from agents import facilitator
from agents import insight_mining
from agents import prompt_coaching
from agents import poll_consensus
from agents import industry_benchmark
from agents import prioritisation_roi
from agents import deck_builder
from agents import opportunity_generation
from agents import scraping_agent
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
    yield
    # Shutdown
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def generate_code(n=6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

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
    """Request to generate a LiveAvatar embed URL for UI/presentation only.
    
    LiveAvatar scope: VIDEO, VOICE, UI only.
    NOT for data processing, AI logic, or backend computation.
    """
    session_code: Optional[str] = None
    participant_name: Optional[str] = None
    participant_role: Optional[str] = None


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
    Create a LiveAvatar embed URL for the frontend iframe.
    
    ⚠️  SCOPE: VIDEO, VOICE, UI only.
    - Generates iframe URLs for avatar video/voice presentation
    - Stores API credentials server-side (browser never sees them)
    - DO NOT pass data processing, AI logic, or backend computation to LiveAvatar
    
    Uses backend-held API credentials so the browser never sees them.
    """
    api_key = os.getenv("LIVEAVATAR_API_KEY", "").strip()
    avatar_id = os.getenv("LIVEAVATAR_AVATAR_ID", "").strip()
    context_id = os.getenv("LIVEAVATAR_CONTEXT_ID", "").strip()
    sandbox = os.getenv("LIVEAVATAR_SANDBOX", "true").strip().lower() in {"1", "true", "yes", "on"}

    if not api_key or not avatar_id or not context_id:
        raise HTTPException(
            503,
            "LiveAvatar is not configured. Set LIVEAVATAR_API_KEY, LIVEAVATAR_AVATAR_ID, and LIVEAVATAR_CONTEXT_ID.",
        )

    payload = {
        "avatar_id": avatar_id,
        "context_id": context_id,
        "is_sandbox": sandbox,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.liveavatar.com/v2/embeddings",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        logger.error("LiveAvatar embed request failed: %s", exc)
        raise HTTPException(502, "Could not reach LiveAvatar right now.")

    if resp.status_code >= 400:
        logger.error("LiveAvatar embed error %s: %s", resp.status_code, resp.text)
        raise HTTPException(502, f"LiveAvatar embed error: {resp.status_code}")

    data = resp.json()
    embed_url = (
        data.get("url")
        or data.get("embed_url")
        or data.get("data", {}).get("url")
        or data.get("data", {}).get("embed_url")
    )
    if not embed_url:
        logger.error("LiveAvatar embed response missing URL: %s", data)
        raise HTTPException(502, "LiveAvatar did not return an embed URL.")

    return {
        "embed_url": embed_url,
        "sandbox": sandbox,
        "avatar_id": avatar_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 0 — Session Setup
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/session/create")
async def create_session(req: CreateSessionRequest):
    code = generate_code()
    while code in sessions:
        code = generate_code()

    # Create session in database
    try:
        db_result = await db.create_session(
            code=code,
            host_name=req.host_name,
            company=req.company,
            industry=req.industry,
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
import httpx

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
    # url = "https://subpatronal-yolanda-promonarchy.ngrok-free.dev/v1/third-party/elevenlabs/proxy/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice_id}/stream"
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
        req.voice_id,
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
