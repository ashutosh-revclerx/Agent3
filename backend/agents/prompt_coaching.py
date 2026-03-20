"""
agents/prompt_coaching.py
─────────────────────────
PROMPT COACHING AGENT
─────────────────────
Responsibility:
  - Evaluates participant prompts on 4 dimensions
  - Rewrites prompts for precision and clarity
  - Runs live AI simulations using the improved prompt
  - Adapts feedback language to participant's AI confidence level

Activated: Exclusively during Activity C
"""
from gemini_client import gemini_json, gemini_text

SCORE_RUBRIC = """
Score each dimension 1–5:
- clarity:     1=vague task, 5=crystal clear what needs to be done
- context:     1=no background, 5=rich context about role/situation/data
- output:      1=no output spec, 5=explicit format, length, structure defined
- constraints: 1=no limits given, 5=clear constraints (what to exclude, edge cases)
"""

CONFIDENCE_FEEDBACK_TONE = {
    1: "Be encouraging and simple. Avoid technical terms. Celebrate what they got right.",
    2: "Be supportive. Explain improvements in plain language with analogies.",
    3: "Be direct and practical. Reference common prompt engineering patterns.",
    4: "Be precise. Use prompt engineering terminology like 'system context' and 'output schema'.",
    5: "Be peer-level. Discuss advanced techniques like chain-of-thought and few-shot examples.",
}


def score_and_improve(prompt: str, task_context: str,
                      company: str, industry: str,
                      confidence_level: int = 3) -> dict:
    """
    Scores the prompt, provides dimension-level feedback, and returns improved version.
    """
    tone = CONFIDENCE_FEEDBACK_TONE.get(confidence_level, CONFIDENCE_FEEDBACK_TONE[3])

    gemini_prompt = f"""You are a prompt engineering coach in an AI strategy workshop.

Participant context: Works at {company} ({industry})
Their background context: {task_context or 'Not provided'}
Their prompt: {prompt}

{SCORE_RUBRIC}

Feedback tone: {tone}

Return JSON only:
{{
  "scores": {{"clarity": 1-5, "context": 1-5, "output": 1-5, "constraints": 1-5}},
  "total_score": <sum of 4 scores>,
  "feedback": {{
    "clarity": "one specific sentence about this dimension",
    "context": "one specific sentence about this dimension",
    "output": "one specific sentence about this dimension",
    "constraints": "one specific sentence about this dimension"
  }},
  "improved_prompt": "The fully rewritten, precision prompt (2–5 sentences)",
  "key_improvement": "One sentence: the single most important change made and why"
}}"""

    result = gemini_json(gemini_prompt)
    if result:
        return result

    # ── Fallback ──
    words     = len(prompt.split())
    has_out   = any(w in prompt.lower() for w in ["output", "format", "return", "list", "write", "give"])
    has_ctx   = len(task_context.strip()) > 20
    clarity   = min(5, max(1, words // 8))
    context   = 4 if has_ctx else 2
    output_s  = 4 if has_out else 2
    const_s   = 2
    total     = clarity + context + output_s + const_s
    improved  = (
        f"{'Context: ' + task_context + '. ' if task_context else ''}"
        f"{prompt.strip()} "
        f"Structure your response with clear headings. "
        f"Flag anything that requires urgent attention. "
        f"Keep the total response under 300 words."
    )
    return {
        "scores": {"clarity": clarity, "context": context, "output": output_s, "constraints": const_s},
        "total_score": total,
        "feedback": {
            "clarity":     "Clear task." if clarity >= 3 else "Specify exactly what action you want the AI to take.",
            "context":     "Good context provided." if has_ctx else "Add your role, company type, and what data is available.",
            "output":      "Output format specified." if has_out else "Tell the AI what the output should look like — format, length, structure.",
            "constraints": "Consider adding what to exclude, the target audience, or length constraints.",
        },
        "improved_prompt": improved,
        "key_improvement": "Added explicit output structure and context to guide the AI toward a consistent, usable response.",
    }


def run_simulation(improved_prompt: str, task_context: str,
                   company: str, industry: str) -> dict:
    """
    Runs a live AI simulation using the improved prompt.
    Uses Gemini with company context as system instruction.
    Returns the output and a one-line insight about what it demonstrates.
    """
    system = (
        f"You are a helpful AI assistant working for {company}, "
        f"a company in the {industry} industry. "
        f"Generate a realistic, genuinely useful response. "
        f"Use plausible but clearly fictional data where needed. "
        f"Show what AI can actually do — make it feel real and immediately valuable."
    )

    full_prompt = f"{system}\n\nTask context: {task_context or 'Not provided'}\n\n{improved_prompt}"

    output = gemini_text(full_prompt)
    if output:
        insight = (
            f"This task was completed in seconds. In production, connected to {company}'s real data, "
            f"this output would be ready to use immediately."
        )
        return {"output": output, "insight": insight}

    return {
        "output": (
            f"**Live simulation requires GEMINI_API_KEY**\n\n"
            f"Add your Gemini API key to backend/.env as GEMINI_API_KEY.\n\n"
            f"Once connected, Claude would process this prompt and return a "
            f"realistic response tailored to {company}'s {industry} context."
        ),
        "insight": "Set GEMINI_API_KEY in your .env to enable live simulations.",
    }