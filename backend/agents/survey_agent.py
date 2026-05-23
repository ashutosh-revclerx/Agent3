"""
agents/survey_agent.py
──────────────────────
SURVEY AGENT
────────────
Responsibility:
  - Generates contextual survey questions using Gemini + coverage map
  - Manages the guided survey coverage structure
  - Extracts structured data from participant responses
  - Adapts vocabulary based on AI maturity score
  - Prioritizes business-goal alignment before AI maturity/IT/pain/concern

Activated: Phase 1 survey (avatar-guided interview)
"""

import logging
from typing import Dict, List, Optional, Literal
from gemini_client import gemini_text
from schemas import CompanyDNA, ParticipantProfile

logger = logging.getLogger("copilot.survey_agent")

# ─────────────────────────────────────────────────────────────────────────────
# Coverage Map & Area Definitions
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_AREAS = [
    "goals_checkup",
    "ai_maturity_personal",
    "ai_maturity_company",
    "it_landscape",
    "pain_points",
    "ai_concerns",
]

AREA_PRIORITY = {area: i for i, area in enumerate(COVERAGE_AREAS)}

# Extraction types for each area
AREA_EXTRACTION = {
    "goals_checkup": None,  # comparison/alignment only
    "ai_maturity_personal": "ai_maturity",  # SMALLINT 1-5
    "ai_maturity_company": "company_ai_maturity",  # VARCHAR
    "it_landscape": "it_tools",  # TEXT[]
    "pain_points": "pain_points",  # TEXT[]
    "ai_concerns": "top_concern",  # TEXT
}

# ─────────────────────────────────────────────────────────────────────────────
# Vocabulary Calibration
# ─────────────────────────────────────────────────────────────────────────────

VOCABULARY_LEVELS = {
    1: "Use only plain business language. No AI acronyms (no 'ML', 'NLP', 'LLM'). Frame everything around outcomes and business impact. Use analogies.",
    2: "Keep language simple and reassuring. Introduce basic AI concepts gently: 'tools that learn patterns', 'automation', 'decision help'. Build confidence step by step.",
    3: "Use standard AI terminology: 'machine learning', 'LLMs', 'AI assistants', 'data quality'. Assume familiarity with basic concepts. Be practical.",
    4: "Engage at a practitioner level. Discuss implementation trade-offs: 'fine-tuning vs. RAG', 'infrastructure', 'model scaling', 'MLOps'. Technical depth is welcome.",
    5: "Use precise technical language: 'transformers', 'embeddings', 'vector databases', 'inference optimization', 'distributed training'. Focus on architecture and strategy.",
}

ROLE_FOCUS = {
    "CEO / Founder": "growth, strategic priorities, cross-functional execution",
    "CTO / Technology Leader": "platform reliability, architecture, delivery bottlenecks",
    "COO / Operations": "process efficiency, handoffs, operational consistency",
    "Product Manager": "roadmap delivery, customer value, cross-team coordination",
    "Data / AI Engineer": "data quality, deployment reliability, model operations",
    "Business Analyst": "reporting quality, data trust, decision support speed",
    "Department Head": "team productivity, dependencies, service quality",
    "Consultant": "client outcomes, implementation risk, adoption barriers",
    "Lead Generation": "lead quality, conversion flow, CRM/process alignment",
}

# ─────────────────────────────────────────────────────────────────────────────
# Welcome Message
# ─────────────────────────────────────────────────────────────────────────────

async def generate_welcome_message(
    participant_name: str,
    company_name: str,
    fun_fact: Optional[str] = None,
    local_context: Optional[str] = None,
) -> str:
    """
    Generate the first message the avatar speaks.
    Structure: greeting + fun fact + local context + survey intro.
    Duration: ~20 seconds (under 60 words).
    
    Rules:
    - Use confirmed data only
    - Skip missing facts (no placeholders)
    - Keep energising and direct
    """
    
    parts = [
        f"Hi {participant_name}! Great to have you here."
    ]
    
    if fun_fact:
        parts.append(fun_fact)
    
    if local_context:
        parts.append(local_context)
    
    parts.append(
        f"Today I'm going to ask you a few questions about {company_name} and where you see "
        "AI fitting into your work. There are no right answers — I just want to understand "
        "your world. Let's start with a quick question about you."
    )
    
    message = " ".join(parts)
    
    # Optional: Use Gemini to polish (but template is usually fine)
    # prompt = f"Concise, energising welcome message (3-5 sentences, <60 words):\n{message}"
    # message = gemini_text(prompt) or message
    
    return message

# ─────────────────────────────────────────────────────────────────────────────
# Company Context Turn
# ─────────────────────────────────────────────────────────────────────────────

async def generate_company_context_message(
    company_name: str,
    company_vision: str,
    company_goals: Optional[List[str]] = None,
) -> str:
    """
    Avatar describes the company, demonstrating knowledge.
    Not a question — a setup for later goals_checkup comparison.
    """
    
    parts = [f"So, {company_name} — {company_vision}."]
    
    if company_goals and len(company_goals) > 0:
        parts.append(company_goals[0])
    
    parts.append(
        "I want to understand how your day-to-day connects to that. Let's get into it."
    )
    
    return " ".join(parts)

# ─────────────────────────────────────────────────────────────────────────────
# Question Generation by Area
# ─────────────────────────────────────────────────────────────────────────────

async def generate_question_for_area(
    area: str,
    participant_name: str,
    company_name: str,
    ai_maturity: Optional[int] = None,
    response_word_count: int = 30,
    context: Optional[Dict] = None,
) -> str:
    """
    Generate a question for a specific coverage area.
    Uses Gemini to create personalised wording while maintaining consistent intent.
    
    Args:
        area: One of COVERAGE_AREAS
        participant_name: For personalization
        company_name: For context
        ai_maturity: To calibrate vocabulary (1-5)
        response_word_count: Average response length to calibrate question depth
        context: Additional context from working memory (extracted fields, prior responses)
    """
    
    context = context or {}
    if ai_maturity is None:
        ai_maturity = 3
    
    vocab_instruction = VOCABULARY_LEVELS.get(ai_maturity, VOCABULARY_LEVELS[3])
    company_vision = (context.get("company_vision") or "").strip()
    company_goals = context.get("company_goals") or []
    goals_text = ", ".join([g for g in company_goals if isinstance(g, str) and g.strip()][:3]) or "not provided"
    participant_role = (context.get("participant_role") or "Business Professional").strip()
    role_focus = ROLE_FOCUS.get(participant_role, "day-to-day work outcomes and cross-team dependencies")
    cross_functional_probe = (
        "Also include a cross-functional angle: ask about problems outside their direct role that still impact their results "
        "(for example handoffs, upstream data quality, approvals, or downstream execution blockers)."
    )
    
    # Base intents for each area
    area_intents = {
        "goals_checkup": (
            f"Ask {participant_name} to compare their view of this year's priorities with the company's website direction. "
            f"Website vision context: {company_vision or 'not provided'}. "
            f"Website goals context: {goals_text}. "
            f"Role context: {participant_role} with focus on {role_focus}. "
            f"Goal: check whether goals collectively match how the business actually operates. "
            f"{cross_functional_probe}"
        ),
        "ai_maturity_personal": (
            f"Ask {participant_name} to rate their personal AI capability or experience (1-5 scale). "
            "Keep it open-ended first, then clarify the scale. "
            f"Examples: 'how comfortable are you using AI tools?' or 'would you say you're experienced with AI?' "
            f"Role context: {participant_role} focused on {role_focus}."
        ),
        "ai_maturity_company": (
            f"Understand where {company_name} is in its AI adoption journey (exploring / piloting / implementing / scaling). "
            "Ask which stage they see their org in, or ask about their current AI use (if any). "
            f"{cross_functional_probe}"
        ),
        "it_landscape": (
            f"Ask what tools {company_name} currently uses for data and automation. "
            "List 2-3 common ones as examples, then ask what they actually use. "
            "Goal: capture CRM, BI, automation platforms, spreadsheets, etc. "
            f"Role context: {participant_role}. {cross_functional_probe}"
        ),
        "pain_points": (
            f"Ask {participant_name} what's slowing their team down. "
            "Start broad: 'what's one thing you wish you could just hand off?' "
            "Then dig into operational friction: manual work, bottlenecks, data silos. "
            f"Ensure at least part of the question targets blockers coming from outside their direct role."
        ),
        "ai_concerns": (
            f"Ask what worries {participant_name} most about AI for their organisation. "
            f"Could be: data privacy, job displacement, hallucinations, cost, security, governance. "
            f"Goal: capture the TOP concern for this person. "
            f"Role context: {participant_role}. {cross_functional_probe}"
        ),
    }
    
    intent = area_intents.get(area, "Ask a thoughtful question.")
    
    # Adjust question depth based on response length
    if response_word_count < 15:
        ask_depth = "Use shorter, more direct questions. The participant gives brief answers."
    elif response_word_count > 50:
        ask_depth = "Ask broader, more open-ended questions. The participant engages deeply."
    else:
        ask_depth = "Mix direct and open-ended questions."
    
    prompt = (
        f"You are an AI strategy consultant conducting a survey for {company_name}.\n"
        f"Participant: {participant_name}\n\n"
        f"Participant role: {participant_role}\n"
        f"Role focus: {role_focus}\n\n"
        f"Tone instruction: {vocab_instruction}\n"
        f"Question depth: {ask_depth}\n\n"
        f"Intent: {intent}\n\n"
        f"Generate ONE question that feels natural and conversational. "
        f"No prefixes like 'Question:' or 'So,'. Just the question. "
        f"Keep it under 30 words. Return only the question text."
    )
    
    question = gemini_text(prompt)
    if not question:
        # Fallback
        return area_intents.get(area, "Tell me more about your work.")
    
    return question.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Response Extraction
# ─────────────────────────────────────────────────────────────────────────────

async def extract_data_from_response(
    area: str,
    participant_response: str,
    ai_maturity: Optional[int] = None,
    context: Optional[Dict] = None,
) -> Dict:
    """
    Extract structured data from a participant's response to a survey question.
    
    Returns a dict of extracted fields for this area, or empty dict if extraction failed.
    """
    
    extraction_fields = AREA_EXTRACTION.get(area)
    if extraction_fields is None:
        return {}  # No extraction for this area
    
    # Convert single field to list for uniform processing
    if isinstance(extraction_fields, str):
        extraction_fields = [extraction_fields]
    
    extracted = {}
    
    for field in extraction_fields:
        prompt = _get_extraction_prompt(area, field, participant_response, ai_maturity)
        
        try:
            value = gemini_text(prompt)
            if value and value.strip().lower() != "none":
                extracted[field] = value.strip()
        except Exception as e:
            logger.error(f"Extraction failed for {area}/{field}: {e}")
    
    return extracted

def _get_extraction_prompt(area: str, field: str, response: str, ai_maturity: Optional[int]) -> str:
    """Build a Gemini prompt tailored to the extraction task."""
    
    extraction_prompts = {
        ("ai_maturity_personal", "ai_maturity"): (
            f"From this response, extract a numeric AI maturity score (1-5).\n"
            f"1 = no experience, 2 = basic awareness, 3 = regular use, 4 = skilled user, 5 = expert/leader\n"
            f"Response: '{response}'\n"
            f"Return ONLY the number 1-5. If you can't determine, return 3."
        ),
        ("ai_maturity_company", "company_ai_maturity"): (
            f"From this response about their company's AI adoption, classify the stage:\n"
            f"- 'exploring': Early investigation, no active projects\n"
            f"- 'piloting': Testing AI in 1-2 controlled projects\n"
            f"- 'implementing': Rolling out AI tools across teams\n"
            f"- 'scaling': Mature AI use across the organization\n"
            f"Response: '{response}'\n"
            f"Return ONLY one of: exploring, piloting, implementing, scaling"
        ),
        ("it_landscape", "it_tools"): (
            f"Extract the tools/platforms mentioned for data, automation, or business operations.\n"
            f"Response: '{response}'\n"
            f"Return a comma-separated list of tool names. E.g.: 'Salesforce, Power BI, Excel'"
        ),
        ("pain_points", "pain_points"): (
            f"Extract the operational pain points or friction areas mentioned.\n"
            f"Response: '{response}'\n"
            f"Return a comma-separated list of pain points. E.g.: 'manual approvals, slow reporting, data silos'"
        ),
        ("ai_concerns", "top_concern"): (
            f"Extract the single biggest concern about AI this person expressed.\n"
            f"Response: '{response}'\n"
            f"Return a short phrase (<10 words). E.g.: 'data privacy and control', 'job displacement'"
        ),
        ("success_definition", "goals_short"): (
            f"Extract the short-term goal (next 3-6 months) they mentioned.\n"
            f"Response: '{response}'\n"
            f"Return a brief goal (<15 words)."
        ),
        ("success_definition", "goals_long"): (
            f"Extract the long-term goal (6-12 months or beyond) they mentioned.\n"
            f"Response: '{response}'\n"
            f"Return a brief goal (<15 words)."
        ),
    }
    
    key = (area, field)
    return extraction_prompts.get(key, f"Extract relevant data from: {response}")

# ─────────────────────────────────────────────────────────────────────────────
# Coverage Map Management
# ─────────────────────────────────────────────────────────────────────────────

def initialize_coverage_map() -> Dict[str, Literal["not_asked", "asked", "answered", "skipped"]]:
    """Create a fresh coverage map with all areas unmarked."""
    return {area: "not_asked" for area in COVERAGE_AREAS}

def get_next_area_to_cover(
    coverage_map: Dict[str, Literal["not_asked", "asked", "answered", "skipped"]],
    last_area: Optional[str] = None,
) -> Optional[str]:
    """
    Determine the next area to cover based on coverage map.
    
    Rules:
    1. If last_area can be followed naturally (thread continuation), stay in that area (asked → answered)
    2. Otherwise, pick the highest-priority uncovered area (not_asked)
    3. If all areas are covered, return None (session complete)
    """
    
    # Check if all areas are covered
    if all(status in ("answered", "skipped") for status in coverage_map.values()):
        return None
    
    # Find the first not_asked area
    for area in COVERAGE_AREAS:
        if coverage_map[area] == "not_asked":
            return area
    
    return None

def is_session_complete(coverage_map: Dict) -> bool:
    """Check if all areas have been answered or skipped."""
    return all(status in ("answered", "skipped") for status in coverage_map.values())

# ─────────────────────────────────────────────────────────────────────────────
# Pace Calibration
# ─────────────────────────────────────────────────────────────────────────────

def get_average_response_length(turn_history: List[Dict]) -> int:
    """Calculate average word count of participant responses so far."""
    if not turn_history:
        return 30
    
    word_counts = [
        len(turn.get("participant_response", "").split())
        for turn in turn_history if "participant_response" in turn
    ]
    
    return sum(word_counts) // len(word_counts) if word_counts else 30
