"""
agents/facilitator.py
─────────────────────
FACILITATOR AGENT
─────────────────
Responsibility:
  - Guides the session flow
  - Generates contextual phase introductions and transition messages
  - Adapts language based on team's AI confidence level (from Activity B)
  - Active throughout ALL phases

Activated: Continuously from Phase 0 through Phase 11
"""
from gemini_client import gemini_text

# Tone templates keyed by avg confidence level (1–5)
TONE_TEMPLATES = {
    1: "Use plain business language. Avoid AI jargon entirely. Focus on outcomes, not technology.",
    2: "Keep language simple and reassuring. Use relatable analogies. Build confidence gently.",
    3: "Use standard AI terminology. Reference familiar tools. Be practical and specific.",
    4: "Engage at a practitioner level. Discuss tradeoffs and implementation considerations.",
    5: "Use precise ML/AI terminology. Focus on architecture, strategy, and differentiation.",
}

PHASE_INTROS = {
    0:  "Let's configure your workshop so the AI can pre-load the right industry context before anyone joins.",
    1:  "Welcome. Let's get to know the people in the room before we start.",
    2:  "Now let's understand where your organisation is trying to go strategically.",
    3:  "Let's surface the operational pain points that are slowing your team down right now.",
    "A": "Before we generate AI ideas, let's be honest about the data you have available.",
    "B": "There are no wrong answers here. We want to understand how your team genuinely feels about AI.",
    "C": "Let's turn a real problem from your work into a live AI demonstration.",
    4:  "Based on everything we've heard, here are the AI opportunities that are most relevant to you.",
    5:  "Cast your first vote — before we show you any external data.",
    6:  "Let's see how companies like yours are actually using AI right now.",
    7:  "Now that you've seen the global picture, cast your second vote.",
    8:  "Let's decide which opportunities to pursue first, based on impact and effort.",
    9:  "Let's measure how ready your organisation actually is to implement AI.",
    10: "Here is your AI implementation roadmap — built entirely from what this team told us today.",
    11: "Your workshop is complete. Here are your deliverables.",
}


def get_phase_intro(phase: int | str, company: str, confidence_level: int = 3) -> str:
    """
    Returns a personalised phase introduction message.
    If Gemini is available, generates a dynamic one.
    Falls back to static template.
    """
    tone = TONE_TEMPLATES.get(confidence_level, TONE_TEMPLATES[3])
    static = PHASE_INTROS.get(phase, "Let's continue.")

    prompt = (
        f"You are facilitating an AI strategy workshop for {company}.\n"
        f"Tone instruction: {tone}\n"
        f"Write a 2-sentence phase introduction for: '{static}'\n"
        f"Keep it energising, direct, and under 40 words. No bullet points."
    )
    result = gemini_text(prompt)
    return result if result else f"{company} — {static}"


def get_transition_message(from_phase: str, to_phase: str, company: str, confidence_level: int = 3) -> str:
    """
    Short transition message shown when host advances to next phase.
    """
    tone = TONE_TEMPLATES.get(confidence_level, TONE_TEMPLATES[3])
    prompt = (
        f"Workshop facilitator for {company}. Tone: {tone}\n"
        f"Write a 1-sentence transition from phase '{from_phase}' to '{to_phase}'.\n"
        f"Acknowledge what was just completed and set up what's next. Max 25 words."
    )
    result = gemini_text(prompt)
    return result if result else f"Great work. Moving on to {to_phase}."


def get_waiting_message(phase: str, submitted: int, total: int) -> str:
    """
    Message shown to participants while waiting for others to submit.
    """
    remaining = total - submitted
    if remaining <= 0:
        return "Everyone has submitted. The host will reveal insights shortly."
    return (
        f"{submitted} of {total} participants have submitted. "
        f"Waiting for {remaining} more response{'s' if remaining > 1 else ''}..."
    )

def get_company_goals_checkup(company: str, existing_objectives: list = None) -> str:
    """
    LLM-generated question to cross-check company's stated strategic goals.
    Phase 1 survey question, persisted to phase_data.company_goals_validated
    """
    from gemini_client import gemini_text
    
    objectives_str = " ".join(existing_objectives) if existing_objectives else "strategic growth"
    
    prompt = (
        f"You are an AI strategy consultant speaking to {company}'s leadership.\n"
        f"They have stated these goals: {objectives_str}\n"
        f"Ask ONE short, probing question (under 20 words) to validate these goals "
        f"and uncover any conflicting priorities or unstated constraints.\n"
        f"Return only the question, no preamble."
    )
    result = gemini_text(prompt)
    return result if result else f"How do these goals align with your current operational priorities at {company}?"


def get_company_ai_maturity_question(company: str, industry: str) -> str:
    """
    LLM-generated question to assess company's AI maturity level.
    Phase 1 survey question, persisted to phase_data.company_ai_maturity
    """
    from gemini_client import gemini_text
    
    prompt = (
        f"You are assessing {company}'s (industry: {industry}) AI readiness.\n"
        f"Generate ONE concise question (under 20 words) that reveals their current AI maturity: "
        f"Are they pre-AI, early-stage pilots, or scaling existing AI?\n"
        f"Make it conversational and non-threatening.\n"
        f"Return only the question, no preamble."
    )
    result = gemini_text(prompt)
    return result if result else f"What's your experience with AI tools and projects so far at {company}?"


def get_it_landscape_question(company: str) -> str:
    """
    LLM-generated question to understand IT infrastructure and tool stack.
    Phase 1 survey question, persisted to phase_data.it_tools
    """
    from gemini_client import gemini_text
    
    prompt = (
        f"You are a technical discovery consultant at {company}.\n"
        f"Ask ONE specific question (under 20 words) about their IT landscape and current tool stack "
        f"(databases, cloud platforms, legacy systems, or data workflow).\n"
        f"Make it natural and non-technical for mixed audiences.\n"
        f"Return only the question, no preamble."
    )
    result = gemini_text(prompt)
    return result if result else f"What are the main systems and platforms your team relies on day-to-day?"


def get_success_definition_prompt(name: str, role: str, company: str) -> str:
    """
    LLM-generated question for participant's personal definition of success.
    Phase 1 upgrade, persisted to phase_data.participant_success_definition
    """
    from gemini_client import gemini_text
    
    prompt = (
        f"You are 1-on-1 with {name}, a {role} at {company}.\n"
        f"Ask ONE open, motivating question (under 25 words) about what personal success "
        f"would look like for them after this workshop — in terms of skills, confidence, or impact.\n"
        f"Make it feel empowering, not corporate.\n"
        f"Return only the question, no preamble."
    )
    result = gemini_text(prompt)
    return result if result else f"What would success look like for you personally after this AI workshop, {name}?"


def process_onboarding_chat(messages, name: str, role: str, department: str) -> dict:
    """
    Handles the interactive voice interview during onboarding.
    Ensures context-aware follow-up questions and limits to MAX_QUESTIONS.
    Returns JSON dict with done, next_question, and extracted_data.
    """
    from gemini_client import gemini_json_with_system
    import traceback
    
    MAX_QUESTIONS = 4
    
    # Extract conversation state
    user_msgs = [m.text for m in messages if m.type == 'user']
    agent_msgs = [m.text for m in messages if m.type == 'agent']
    num_user_replies = len(user_msgs)
    latest_user_msg = user_msgs[-1].strip() if user_msgs else ""
    
    # Step 0: User said hello → ask the first real question
    is_greeting = latest_user_msg.lower() in ['hello', 'hi', 'hey', 'hi there', 'hello!', 'hey!', 'start', 'hey there']
    
    if is_greeting or num_user_replies == 0:
        first_q = f"Great to have you here! As a {role}, I'd love to understand your work. Can you walk me through what a typical workday looks like for you — the main tasks, tools, and how information flows?"
        return {"done": False, "next_question": first_q}
    
    # Step 1+: We have real user answers — use the LLM for contextual follow-ups
    num_real_answers = len([u for u in user_msgs if u.lower() not in ['hello', 'hi', 'hey', 'hi there', 'hello!', 'hey!', 'start', 'hey there']])
    is_last_chance = (num_real_answers >= MAX_QUESTIONS)
    too_early = (num_real_answers < 2)
    
    history = "\n".join([f"{m.type.capitalize()}: {m.text}" for m in messages[-12:]])
    
    sys_prompt = f"""You are a friendly AI facilitator having a voice conversation with {name or 'a participant'}, a {role} from {department}.

YOUR GOAL: Understand their daily workflow and biggest challenges so you can recommend AI solutions.

CONVERSATION STATE: {num_real_answers} substantive answers received. {"FINAL TURN — wrap up now." if is_last_chance else ""}

HOW TO RESPOND:
- Start by briefly acknowledging something SPECIFIC the user just said (e.g. "So you spend a lot of time on [X]...")
- Then ask ONE short follow-up question (under 20 words) that digs deeper into what they described.
- Your follow-up should focus on: tools used, time spent, manual vs automated, pain points, or errors.

{"You MUST set done to false — you need more information." if too_early else ""}
{"You MUST set done to true and provide extracted_data now." if is_last_chance else ""}

Output ONLY valid JSON:
{{
  "done": {str(is_last_chance).lower()},
  "next_question": "acknowledgment + follow-up question",
  "closing_message": "brief closing (only if done is true)",
  "extracted_data": {{
     "daily_work": "summary of their workflow",
     "top_challenge": "summary of their main pain point"
  }}
}}"""
    
    prompt = f"Conversation:\n{history}\n\nJSON:"
    
    try:
        res = gemini_json_with_system(prompt, sys_prompt)
        print(f"[facilitator-chat] LLM response: {res}")
    except Exception as e:
        print(f"[facilitator-chat] LLM error: {e}")
        traceback.print_exc()
        res = None
    
    # ── Fallback: build a contextual follow-up from the user's own words ──
    if not res or not isinstance(res, dict):
        print(f"[facilitator-chat] Using fallback. num_real_answers={num_real_answers}")
        
        # Extract keywords from the user's last message for context
        last_words = latest_user_msg.split()
        snippet = " ".join(last_words[:8]) if len(last_words) > 3 else latest_user_msg
        
        if is_last_chance or num_real_answers >= 3:
            return {
                "done": True,
                "closing_message": "Thanks for sharing all of that — I have a good picture now. Let's move forward!",
                "extracted_data": {
                    "daily_work": " ".join(user_msgs[:2]) if len(user_msgs) >= 2 else latest_user_msg,
                    "top_challenge": user_msgs[-1] if len(user_msgs) > 1 else ""
                }
            }
        
        # Contextual fallbacks that reference the user's answer
        fallbacks_by_step = [
            f"Thanks for sharing that. You mentioned \"{snippet}\" — what tools or software do you use for that?",
            f"Got it. Of everything you've described, what feels the most repetitive or time-consuming?",
            f"That's helpful. What's the biggest challenge or bottleneck you face in your current workflow?",
        ]
        idx = min(num_real_answers - 1, len(fallbacks_by_step) - 1)
        return {"done": False, "next_question": fallbacks_by_step[max(0, idx)]}
    
    # ── Server-side enforcement ──
    if too_early and res.get("done"):
        res["done"] = False
    
    if is_last_chance:
        res["done"] = True
        if not res.get("closing_message"):
            res["closing_message"] = "Thanks — I have a clear picture. Let's continue."
        if not res.get("extracted_data"):
            res["extracted_data"] = {
                "daily_work": " ".join(user_msgs[:2]),
                "top_challenge": user_msgs[-1] if len(user_msgs) > 1 else ""
            }
    
    return res
