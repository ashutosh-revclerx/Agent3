"""
agents/prompt_coaching.py
─────────────────────────
PROMPT COACHING AGENT
─────────────────────
Responsibility:
  - Generates a role-specific scenario for the participant
  - Evaluates prompts AGAINST that specific scenario
  - Rewrites prompts for precision
  - Runs live Gemini simulation using the scenario as context

Activated: Exclusively during Activity C
"""
from gemini_client import gemini_json, gemini_text
import uuid

CONFIDENCE_FEEDBACK_TONE = {
    1: "Be encouraging and simple. Avoid technical terms. Celebrate what they got right.",
    2: "Be supportive. Explain improvements in plain language with analogies.",
    3: "Be direct and practical. Reference common prompt engineering patterns.",
    4: "Be precise. Use prompt engineering terminology like system context and output schema.",
    5: "Be peer-level. Discuss advanced techniques like chain-of-thought and few-shot examples.",
}

# Role-specific scenario templates used as fallback
ROLE_SCENARIOS = {
    "CEO / Founder": {
        "title": "Board meeting preparation — revenue variance report",
        "situation": "Your board meeting is in 3 hours. The CFO has just sent you a CSV with last quarter's revenue by product line and region. Revenue is down 12% overall but you don't know which areas are driving the decline or why. You need to walk into that meeting with a clear narrative.",
        "task": "Write a prompt that instructs an AI to analyse the revenue data, identify the top 3 drivers of the decline, compare against the previous quarter, and produce a 5-bullet executive summary you can present to the board.",
        "data_available": ["Revenue CSV by product line and region", "Previous quarter comparison data", "Target vs actual figures"],
        "expected_output": "A concise executive brief: top decline drivers, % contribution each, one-line context per driver, and a recommended talking point.",
    },
    "CTO / Technology Leader": {
        "title": "Production incident — post-mortem analysis",
        "situation": "Your payment service went down for 47 minutes this morning. You have the full server log file (2,800 lines), a timeline of alerts, and the on-call engineer's notes. The CEO wants a post-mortem report by end of day and the team needs a root cause within the hour.",
        "task": "Write a prompt that instructs an AI to analyse the log file and notes, identify the root cause, build a clear incident timeline, and draft a post-mortem report with action items.",
        "data_available": ["Server log file (2,800 lines)", "Alert timeline with timestamps", "On-call engineer's notes"],
        "expected_output": "A structured post-mortem: timeline, root cause, contributing factors, customer impact, and 3-5 specific action items with owners.",
    },
    "COO / Operations": {
        "title": "Weekly ops review — SLA breach investigation",
        "situation": "Three customers have raised SLA breaches this week. Your ops team has sent you separate spreadsheets from customer support, logistics, and fulfilment — each using different column names for the same data. The weekly leadership review is in 2 hours and you need a single consolidated view.",
        "task": "Write a prompt that instructs an AI to consolidate the three spreadsheets, identify the common thread in the SLA breaches, and produce a one-page ops summary with the root cause and recommended fix.",
        "data_available": ["Support team spreadsheet", "Logistics team spreadsheet", "Fulfilment team spreadsheet"],
        "expected_output": "A consolidated ops summary: unified breach list, common root cause, affected customers, and 2-3 prioritised remediation steps.",
    },
    "Product Manager": {
        "title": "Feature prioritisation — user feedback analysis",
        "situation": "You have 340 pieces of user feedback collected over the last 6 weeks from in-app surveys, support tickets, and app store reviews. Your quarterly planning session is tomorrow and you need to walk in with a data-backed prioritisation recommendation for the next sprint.",
        "task": "Write a prompt that instructs an AI to categorise all 340 feedback items by theme, identify the top 5 feature requests by frequency and sentiment, and produce a prioritised feature recommendation with supporting evidence.",
        "data_available": ["340 user feedback items (mixed format)", "In-app survey responses", "Support ticket summaries", "App store reviews"],
        "expected_output": "A prioritised feature list: top 5 themes with frequency count, representative quotes per theme, and a recommended sprint priority order with rationale.",
    },
    "Data / AI Engineer": {
        "title": "Pipeline failure — data quality investigation",
        "situation": "Your nightly ETL pipeline failed at 2am. The downstream analytics dashboard is showing NULL values for 8 key metrics that stakeholders check every morning. You have the pipeline error logs, the source data sample, and the transformation code. It is now 7am and stakeholders are already messaging.",
        "task": "Write a prompt that instructs an AI to analyse the error logs and source data, identify the data quality issue causing the NULLs, suggest the specific fix, and draft a stakeholder update message.",
        "data_available": ["Pipeline error logs", "Source data sample (first 100 rows)", "Transformation SQL/Python code"],
        "expected_output": "Root cause identified with line reference, specific code fix, and a clear 3-sentence stakeholder update suitable for a Slack message.",
    },
    "Business Analyst": {
        "title": "Monthly report — finance data reconciliation",
        "situation": "It is the last working day of the month. You have three data exports: one from the ERP, one from the CRM, and one from the billing system. The numbers don't match — total revenue differs by £23,400 across the three systems. The Finance Director needs the reconciled figure in 90 minutes.",
        "task": "Write a prompt that instructs an AI to compare the three datasets, identify where the £23,400 discrepancy is coming from, and produce a reconciliation note with the corrected figure and explanation.",
        "data_available": ["ERP revenue export", "CRM revenue export", "Billing system export"],
        "expected_output": "A reconciliation note: identified discrepancy source, which system is correct and why, corrected total, and a 2-sentence explanation suitable for the Finance Director.",
    },
    "Department Head": {
        "title": "Team performance review — quarterly assessment",
        "situation": "You have your quarterly 1-1s with 8 direct reports starting tomorrow. HR has sent you each person's KPI data, attendance record, and peer feedback summary. You need to prepare personalised talking points for each person — noting wins, areas to improve, and development suggestions — but you only have 2 hours this afternoon.",
        "task": "Write a prompt that instructs an AI to analyse each team member's data and produce a structured preparation note per person with 3 wins, 1-2 development areas, and one specific growth suggestion.",
        "data_available": ["KPI performance data per person", "Attendance and leave records", "Peer feedback summaries"],
        "expected_output": "8 individual prep notes, each with: 3 specific wins with data references, 1-2 honest development areas, and one actionable growth suggestion.",
    },
    "Consultant": {
        "title": "Client proposal — AI opportunity assessment",
        "situation": "A new client has sent you their annual report, an org chart, and a list of their top 5 strategic priorities. They want a first-pass AI opportunity assessment before next week's discovery call. You have 4 hours to produce something credible and tailored.",
        "task": "Write a prompt that instructs an AI to analyse the documents and identify the top 3 AI use cases for this client, with estimated impact, implementation complexity, and a suggested first quick win.",
        "data_available": ["Client annual report (PDF)", "Org chart", "List of 5 strategic priorities"],
        "expected_output": "A 1-page AI opportunity brief: top 3 use cases with impact/complexity ratings, one recommended quick win with rationale, and 3 discovery questions to validate the assessment.",
    },
    "Other": {
        "title": "Weekly status update — manual reporting task",
        "situation": "Every Friday afternoon you spend 90 minutes compiling the weekly status report. You pull numbers from 4 different systems, copy them into a spreadsheet, write a summary paragraph, and email it to 12 stakeholders. This week you have a client call that runs until 5pm but the report is due at 5:30pm.",
        "task": "Write a prompt that instructs an AI to take your raw data and produce the formatted weekly status report, including a summary paragraph and key highlights, ready to send.",
        "data_available": ["Raw numbers from 4 systems", "Last week's report as template reference", "List of 12 stakeholder names"],
        "expected_output": "A formatted weekly status report: key metrics table, 1-paragraph executive summary, 3 highlights, and 1 risk or item to watch.",
    },
}

DEFAULT_SCENARIO = ROLE_SCENARIOS["Other"]


# ─────────────────────────────────────────────────────────────────────────────
# Generate scenario
# ─────────────────────────────────────────────────────────────────────────────

def generate_scenario(role: str, department: str, company: str, industry: str) -> dict:
    """
    Generates a realistic, role-specific scenario for Activity C.
    The user must write a prompt that handles this specific situation.
    """
    prompt = f"""You are designing a prompt engineering exercise for a workshop participant.

Their role: {role}
Their department: {department}
Their company: {company}
Industry: {industry}

Create a realistic, specific work scenario that this person would actually encounter.
The scenario should:
- Be believable for someone in this exact role and department
- Involve a time pressure (makes it feel real and urgent)
- Have clear data inputs that an AI could work with
- Have a specific deliverable the AI needs to produce

Return JSON only:
{{
  "id": "unique short string e.g. scenario_cto_001",
  "title": "Short descriptive title (5-8 words)",
  "situation": "2-3 sentences describing the specific work situation. Include the time constraint and the problem they face.",
  "task": "1-2 sentences describing exactly what they need the AI to do. Be specific about inputs and outputs.",
  "data_available": ["list", "of", "3-5", "specific data sources they have access to"],
  "expected_output": "1 sentence describing what a great AI output would look like for this scenario."
}}

Make it realistic and specific — not generic. A CTO scenario should feel different from a COO scenario.
Return ONLY the JSON."""

    result = gemini_json(prompt)
    if result and all(k in result for k in ["title", "situation", "task"]):
        result["id"] = result.get("id", f"scenario_{role.lower().replace(' ','_')[:10]}")
        return result

    # Fallback to static scenario
    fallback = ROLE_SCENARIOS.get(role, DEFAULT_SCENARIO).copy()
    fallback["id"] = f"fallback_{role.lower().replace(' ','_')[:10]}"
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# Score and improve — evaluated AGAINST the scenario
# ─────────────────────────────────────────────────────────────────────────────

SCORE_RUBRIC = """
Score each dimension 1-5 specifically in the context of the scenario provided:
- clarity:     Does the prompt clearly state the specific task from the scenario?
- context:     Does it reference the actual data and situation from the scenario?
- output:      Does it specify the exact output format needed for this scenario?
- constraints: Does it include relevant constraints (time, format, audience, length)?
"""

def score_and_improve(prompt: str, task_context: str, company: str, industry: str,
                      confidence_level: int = 3, scenario: dict = None) -> dict:
    """
    Scores the prompt against the specific scenario.
    Returns scores, per-dimension feedback, improved version, and scenario alignment note.
    """
    tone = CONFIDENCE_FEEDBACK_TONE.get(confidence_level, CONFIDENCE_FEEDBACK_TONE[3])

    scenario_context = ""
    if scenario:
        scenario_context = f"""
The participant was given this specific scenario to respond to:
Title: {scenario.get('title', '')}
Situation: {scenario.get('situation', '')}
Task: {scenario.get('task', '')}
Data available: {', '.join(scenario.get('data_available', []))}
Expected output: {scenario.get('expected_output', '')}

Evaluate the prompt specifically against this scenario — does it address the right problem, 
reference the right data, and request the right output format?"""

    gemini_prompt = f"""You are a prompt engineering coach in an AI strategy workshop.

Company: {company} | Industry: {industry}
{scenario_context}

Participant's prompt:
{prompt}

{SCORE_RUBRIC}

Feedback tone: {tone}

Return JSON only:
{{
  "scores": {{"clarity": 1-5, "context": 1-5, "output": 1-5, "constraints": 1-5}},
  "total_score": <sum>,
  "feedback": {{
    "clarity":     "one specific sentence referencing the scenario",
    "context":     "one specific sentence referencing the scenario data",
    "output":      "one specific sentence about the expected output",
    "constraints": "one specific sentence about missing or good constraints"
  }},
  "improved_prompt": "A fully rewritten prompt that specifically handles this scenario — reference the actual data sources and output format from the scenario",
  "key_improvement": "One sentence explaining the most important change and why it matters for THIS scenario",
  "scenario_alignment": "One sentence on how well the prompt addresses the specific scenario vs being too generic"
}}"""

    result = gemini_json(gemini_prompt)
    if result:
        return result

    # ── Fallback ──
    words     = len(prompt.split())
    has_out   = any(w in prompt.lower() for w in ["output", "format", "return", "list", "write", "produce", "give"])
    has_ctx   = len(task_context.strip()) > 20 or (scenario is not None)
    clarity   = min(5, max(1, words // 8))
    context   = 4 if has_ctx else 2
    output_s  = 4 if has_out else 2
    const_s   = 2
    total     = clarity + context + output_s + const_s

    base = scenario.get('task', task_context) if scenario else task_context
    improved = (
        f"You are an AI assistant helping a {company} team member. "
        f"Context: {base} "
        f"Using the provided data, complete this task and structure your response clearly. "
        f"Format: use headers and bullet points. Keep the response under 400 words. "
        f"Flag any data quality issues or assumptions you make."
    )
    return {
        "scores": {"clarity": clarity, "context": context, "output": output_s, "constraints": const_s},
        "total_score": total,
        "feedback": {
            "clarity":     "Good task description." if clarity >= 3 else "Be more specific about the exact task from the scenario.",
            "context":     "References the scenario context." if has_ctx else "Explicitly reference the data sources from the scenario.",
            "output":      "Output format specified." if has_out else "Specify exactly what the output should look like for this scenario.",
            "constraints": "Consider adding the audience, length limit, or tone constraints relevant to this situation.",
        },
        "improved_prompt": improved,
        "key_improvement": "The improved prompt explicitly references the scenario data and specifies a structured output format.",
        "scenario_alignment": "The prompt partially addresses the scenario but could be more specific about the data inputs and deliverable format.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Run simulation — uses scenario as the grounding context
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(improved_prompt: str, task_context: str,
                   company: str, industry: str,
                   scenario: dict = None) -> dict:
    """
    Runs a live simulation using the improved prompt.
    The scenario provides realistic fictional data for the simulation.
    """
    scenario_data = ""
    time_saved    = None

    if scenario:
        scenario_data = f"""
Scenario context for this simulation:
{scenario.get('situation', '')}

Data you have available:
{chr(10).join(f"- {d}" for d in scenario.get('data_available', []))}

For this simulation, invent realistic but clearly fictional sample data that matches 
what this person would actually have. Make the output feel genuinely useful."""

        # Estimate time saving based on role
        time_map = {
            "CEO / Founder":           "Saves ~45 minutes of manual analysis before a board meeting",
            "CTO / Technology Leader": "Saves ~2 hours of log analysis — incident resolved before stakeholders notice",
            "COO / Operations":        "Saves ~90 minutes of spreadsheet work across 3 systems",
            "Product Manager":         "Saves ~3 hours of manual feedback categorisation",
            "Data / AI Engineer":      "Saves ~1 hour of debugging — root cause found before 9am standup",
            "Business Analyst":        "Saves ~2 hours of reconciliation work, delivered in under 2 minutes",
            "Department Head":         "Saves ~2.5 hours of prep — 8 structured notes instead of blank page",
            "Consultant":              "Saves ~3 hours of research — credible first-pass assessment in minutes",
        }
        role = scenario.get("role", "")
        time_saved = time_map.get(role, "Saves significant manual time for this workflow")

    system = (
        f"You are a helpful AI assistant working for {company}, a {industry} company. "
        f"Generate a realistic, immediately useful response. "
        f"Use plausible but clearly fictional data. "
        f"Make it feel like a real work output — formatted, specific, actionable."
        f"{scenario_data}"
    )

    output = gemini_text(improved_prompt, system=system)
    if output:
        insight = (
            f"This output was generated in seconds. Connected to {company}'s real data, "
            f"this would be production-ready immediately."
        )
        return {"output": output, "insight": insight, "time_saved": time_saved}

    return {
        "output": (
            f"**Live simulation requires GEMINI_API_KEY**\n\n"
            f"Add your Gemini API key to backend/.env.\n"
            f"Once connected, the AI would process this scenario and return a "
            f"realistic, immediately useful output for {company}."
        ),
        "insight": "Set GEMINI_API_KEY in your .env to enable live simulations.",
        "time_saved": None,
    }