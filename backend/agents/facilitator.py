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