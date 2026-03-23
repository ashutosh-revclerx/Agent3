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
"""
import uuid, random, string, datetime, json, asyncio, os
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ── Import all 7 agents ───────────────────────────────────────────────────────
from agents import facilitator
from agents import insight_mining
from agents import prompt_coaching
from agents import poll_consensus
from agents import industry_benchmark
from agents import prioritisation_roi
from agents import deck_builder
from seed_context import seed_session, build_system_prompt, get_department_names, BUSINESS_CONTEXT

app = FastAPI(title="AI Consulting Copilot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Stores  (swap for PostgreSQL in production)
# ─────────────────────────────────────────────────────────────────────────────
sessions:      dict = {}   # code → session
participants:  dict = {}   # id   → participant
phase_data:    dict = {}   # code → { phase_key: [submissions] }
ws_connections:dict = {}   # code → [WebSocket]


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
    participant_count: int;  duration_mins: int = 90

class JoinRequest(BaseModel):
    session_code: str;  name: str;  role: str
    department: str;  top_challenge: str;  ai_confidence: int

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

class RevealRequest(BaseModel):
    session_code: str;  phase: str


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


# ─────────────────────────────────────────────────────────────────────────────
# Phase 0 — Session Setup
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/session/create")
def create_session(req: CreateSessionRequest):
    code = generate_code()
    while code in sessions:
        code = generate_code()

    session = {
        "id": str(uuid.uuid4()), "code": code,
        "host_name": req.host_name, "company": req.company,
        "industry": req.industry, "participant_count": req.participant_count,
        "duration_mins": req.duration_mins, "current_phase": 0,
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

    # Agent 1: generate phase 0 intro message (now seed-aware)
    intro = facilitator.get_phase_intro(0, req.company)
    print(f"✅ Session: {code} | {req.company} | {req.industry}")
    print(f"   Seeded: {len(session['known_departments'])} departments, {len(session['pillar_names'])} pillars")
    return {**session, "intro_message": intro}


@app.get("/session/{code}")
def get_session(code: str):
    code = code.upper()
    if code not in sessions:
        raise HTTPException(404, f"Session '{code}' not found")
    return sessions[code]

@app.get("/session/{code}/participants")
def get_participants(code: str):
    code = code.upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[code]
    return {"session_code": code, "count": len(s["participants"]),
            "participants": [participants[pid] for pid in s["participants"] if pid in participants]}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Participant Onboarding
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/participant/join")
async def join_participant(req: JoinRequest):
    code = req.session_code.upper()
    if code not in sessions:
        raise HTTPException(404, "Session not found")
    p = {
        "id": str(uuid.uuid4()), "session_code": code,
        "name": req.name, "role": req.role, "department": req.department,
        "top_challenge": req.top_challenge, "ai_confidence": req.ai_confidence,
        "joined_at": datetime.datetime.utcnow().isoformat(),
    }
    sessions[code]["participants"].append(p["id"])
    participants[p["id"]] = p
    await broadcast(code, {"type": "participant_joined", "count": len(sessions[code]["participants"]), "name": req.name})
    print(f"👤 {req.name} ({req.role}) → {code}")
    return p


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

    # On Poll 2, compute vote shift
    shift = None
    if req.poll_number == 2:
        poll1 = s["workshop_data"].get("poll1_results", [])
        shift = poll_consensus.measure_vote_shift(poll1, results)
        s["workshop_data"]["poll2_results"] = results
        s["workshop_data"]["vote_shift"]    = shift
    else:
        s["workshop_data"]["poll1_results"] = results

    await broadcast(code, {"type": f"poll_{req.poll_number}_update", "results": results, "consensus": consensus})
    return {"results": results, "consensus": consensus, "shift": shift}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — Industry Benchmark  [Agent 5: Industry Benchmark]
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/phase/benchmark/{session_code}")
async def get_benchmark(session_code: str):
    code = session_code.upper()
    if code not in sessions: raise HTTPException(404, "Session not found")
    s = sessions[code]

    org_use_cases = [uc.get("title", "") for uc in s["workshop_data"].get("use_cases", [])]
    enriched      = industry_benchmark.enrich_with_gemini(s["industry"], s["company"], org_use_cases)
    s["workshop_data"]["benchmark"] = enriched

    await broadcast(code, {"type": "benchmark_ready", "data": enriched})
    return enriched


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
    from fastapi.responses import StreamingResponse
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        # Return a tiny silent MP3 so the frontend doesn't break
        raise HTTPException(503, "ELEVENLABS_API_KEY not set — voice disabled")

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

    async def stream_audio():
        async with httpx.AsyncClient(timeout=20) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    return
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    yield chunk

    return StreamingResponse(stream_audio(), media_type="audio/mpeg")


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
