"""
agents/insight_mining.py
────────────────────────
INSIGHT MINING AGENT
────────────────────
Responsibility:
  - Clusters participant responses into strategic themes
  - Detects cross-department patterns
  - Builds the business objective map (Phase 2)
  - Clusters operational problems (Phase 3)
  - Surfaces strategic observations in real time

Activated: Phase 2 through Phase 3 (continuously)
"""
from gemini_client import gemini_json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from seed_context import build_system_prompt, get_all_pain_points
from .industry_benchmark import get_industry_benchmarks


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Business Objective Map
# ─────────────────────────────────────────────────────────────────────────────
def build_objective_map(company: str, industry: str, objectives: list,
                        growth_areas: list, challenges: str,
                        session: dict = None, participant_role: str = "Other") -> dict:
    """
    Analyses strategic objectives, growth priorities, and challenge text.
    Returns a business objective map with themed clusters.
    """
    role_context = f"This response comes from a participant with the role: {participant_role}. " \
        f"Interpret their objectives and challenges through the lens of that role. " \
        f"Use role-appropriate language in summaries and AI opportunities."

    prompt = f"""You are an AI strategy analyst in a live consulting workshop.

Organisation: {company}
Industry: {industry}
Participant role: {participant_role}
Strategic objectives selected: {', '.join(objectives)}
Growth priorities: {', '.join(growth_areas)}
Operational challenges described: {challenges}

{role_context}

Generate a business objective map. Return JSON only:
{{
  "dominant_theme": "One sentence: the overarching strategic priority",
  "clusters": [
    {{
      "icon": "◈",
      "theme": "Cluster name (2–4 words)",
      "signals": 3,
      "summary": "What this cluster tells us about the organisation (2 sentences)",
      "ai_potential": "One specific, concrete AI use case that addresses this cluster"
    }}
  ]
}}

Rules:
- Create 2–4 clusters
- Each cluster must combine at least 2 related inputs
- ai_potential must be concrete, not generic (e.g. 'AI-powered lead scoring' not 'use AI')
- Return ONLY the JSON"""

    result = gemini_json(prompt)
    if result:
        return result

    # ── Fallback (runs when GEMINI_API_KEY is not set) ──
    # Match on label text since frontend now sends labels, not IDs
    obj_text = " ".join(objectives).lower()
    growth_text = " ".join(growth_areas).lower()

    clusters = []

    # Cluster 1 — Growth / commercial signals
    growth_keywords = ["revenue", "growth", "market", "customer", "retention", "sales", "product", "innovation", "monetis"]
    if any(k in obj_text or k in growth_text for k in growth_keywords):
        obj_matches = [o for o in objectives if any(k in o.lower() for k in growth_keywords)]
        clusters.append({
            "icon": "◆",
            "theme": "Growth & Customer Intelligence",
            "signals": max(2, len(obj_matches) + 1),
            "summary": (
                f"{company} is prioritising revenue expansion and customer experience improvement. "
                f"Growth is the dominant commercial driver this year, with {len(growth_areas)} growth "
                f"priorities identified."
            ),
            "ai_potential": "AI-powered customer segmentation and automated personalised engagement across the funnel"
        })

    # Cluster 2 — Operational / tech signals
    ops_keywords = ["efficiency", "operational", "automat", "manual", "data", "infrastructure", "velocity", "platform", "integration", "pipeline", "process"]
    if any(k in obj_text or k in growth_text or k in challenges.lower() for k in ops_keywords):
        clusters.append({
            "icon": "◈",
            "theme": "Operational & Technical Efficiency",
            "signals": max(2, len([o for o in objectives if any(k in o.lower() for k in ops_keywords)])),
            "summary": (
                f"Manual processes and data silos are limiting {company}'s productivity. "
                f"The team is spending significant time on work that AI tools can automate — "
                f"particularly in the areas highlighted in the challenges described."
            ),
            "ai_potential": "Intelligent workflow automation with AI-generated dashboards and anomaly alerting"
        })

    # Cluster 3 — Risk / compliance signals
    risk_keywords = ["risk", "compliance", "security", "governance", "legal", "regulation"]
    if any(k in obj_text or k in growth_text for k in risk_keywords):
        clusters.append({
            "icon": "▣",
            "theme": "Risk & Governance",
            "signals": 2,
            "summary": (
                f"{company} has identified compliance and risk management as strategic priorities. "
                f"AI can reduce manual audit work and flag issues before they escalate."
            ),
            "ai_potential": "Automated compliance monitoring, contract review AI, and real-time risk alerting"
        })

    # Cluster 4 — Talent / people signals
    people_keywords = ["talent", "people", "hr", "team", "workforce", "hiring", "productivity"]
    if any(k in obj_text or k in growth_text for k in people_keywords):
        clusters.append({
            "icon": "◉",
            "theme": "Talent & Workforce Productivity",
            "signals": 2,
            "summary": (
                f"People productivity and talent development are strategic priorities for {company}. "
                f"AI can reduce administrative overhead and free teams for higher-value work."
            ),
            "ai_potential": "AI-assisted onboarding, performance insight dashboards, and automated HR reporting"
        })

    # Default if nothing matched
    if not clusters:
        clusters.append({
            "icon": "◎",
            "theme": "Strategic AI Readiness",
            "signals": len(objectives) + len(growth_areas),
            "summary": (
                f"{company} is mapping where AI can create the most value across its operations. "
                f"This workshop will prioritise the highest-impact, lowest-effort opportunities first."
            ),
            "ai_potential": "Targeted AI pilots in the highest-friction workflows identified today"
        })

    # Build a readable dominant theme from actual objective labels
    top_objectives = objectives[:2] if objectives else ["operational improvement"]
    dominant = (
        f"{company} is primarily focused on {' and '.join(top_objectives).lower()}, "
        f"with {len(growth_areas)} growth priorities driving the agenda this year."
    )

    return {"dominant_theme": dominant, "clusters": clusters}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Problem Clustering
# ─────────────────────────────────────────────────────────────────────────────
def cluster_problems(company: str, industry: str, problems: list,
                       session: dict = None) -> list:
    """
    Takes a list of submitted problems and clusters them into strategic themes.
    Detects cross-department patterns and assigns AI opportunities.
    Merges with seed pain points for richer clustering.
    """
    if not problems:
        return []
    # Merge participant problems with seeded pain points for richer context
    seed_problems = []
    if session and session.get("seed", {}).get("insight_mining", {}).get("known_pain_points"):
        seed_problems = session["seed"]["insight_mining"]["known_pain_points"][:10]

    problems_text = "\n".join([
        f"- [{p.get('department', 'Unknown')}] \"{p['text']}\" "
        f"(severity: {p['severity']}/5, tags: {', '.join(p.get('tags', []))})"
        for p in problems
    ])

    prompt = f"""You are an AI strategy consultant clustering operational problems in a workshop.

Organisation: {company} | Industry: {industry}

Problems submitted by participants:
{problems_text}

Group into 2–4 strategic clusters. Return a JSON array only:
[
  {{
    "icon": "◈",
    "theme": "Theme name (3–5 words)",
    "problem_count": 2,
    "summary": "What this cluster reveals about the organisation (2 sentences)",
    "departments": ["Sales", "Finance"],
    "cross_department": true,
    "avg_severity": 3.5,
    "ai_opportunity": "Specific AI solution addressing all problems in this cluster"
  }}
]

Rules:
- cross_department = true if problems come from 2+ different departments
- avg_severity = average of the severity scores in this cluster
- ai_opportunity must be specific (name the type of AI system)
- Return ONLY the JSON array"""

    result = gemini_json(prompt)
    if result and isinstance(result, list):
        return result

    # ── Fallback ──
    departments = list(set(p.get('department', 'General') for p in problems if p.get('department')))
    avg_sev     = sum(p.get('severity', 3) for p in problems) / max(len(problems), 1)
    manual      = [p for p in problems if 'Manual' in p.get('tags', [])]
    time_cons   = [p for p in problems if 'Time-consuming' in p.get('tags', [])]
    clusters    = []

    if manual:
        # Extract workflow steps for fallback
        wf_steps = []
        for p in manual:
            wf = p.get('workflow_description', '').strip()
            if wf:
                sentences = [s.strip() for s in wf.replace('then', '.').split('.') if len(s.strip()) > 8]
                wf_steps.extend(sentences[:2])
        clusters.append({
            "icon": "◈", "theme": "Manual Process Overhead",
            "problem_count": len(manual),
            "summary": "Teams are spending significant time on repetitive manual tasks. This work is directly automatable with AI.",
            "departments": departments[:3], "cross_department": len(departments) > 1,
            "avg_severity": round(avg_sev, 1),
            "ai_opportunity": "RPA + AI workflow agents to eliminate manual data entry and repetitive processing",
            "automation_targets": wf_steps[:4] if wf_steps else [],
            "manual_steps_identified": len(wf_steps),
        })
    if time_cons:
        clusters.append({
            "icon": "◆", "theme": "Slow Decisions & Reporting",
            "problem_count": len(time_cons),
            "summary": "Reporting and decision workflows are too slow. Real-time AI analytics would eliminate the lag.",
            "departments": departments[:2], "cross_department": len(departments) > 1,
            "avg_severity": round(min(avg_sev + 0.3, 5.0), 1),
            "ai_opportunity": "AI reporting pipeline with natural language querying and automated alerts",
            "automation_targets": [],
            "manual_steps_identified": 0,
        })
    if not clusters:
        clusters.append({
            "icon": "◎", "theme": "Operational Friction Points",
            "problem_count": len(problems),
            "summary": f"{company} has identified several high-priority areas for AI automation. These represent the best starting points.",
            "departments": departments, "cross_department": len(departments) > 1,
            "avg_severity": round(avg_sev, 1),
            "ai_opportunity": "Targeted AI pilots in the workflows with the highest severity scores",
            "automation_targets": [],
            "manual_steps_identified": 0,
        })
    return clusters


# ─────────────────────────────────────────────────────────────────────────────
# Cross-session pattern detection
# ─────────────────────────────────────────────────────────────────────────────
def detect_sector_overlap(industry: str, problem_themes: list) -> list:
    """
    Returns which problem themes are commonly seen across the industry.
    Used to add 'sector-validated' signals to use case cards in Phase 4.
    """
    benchmarks = get_industry_benchmarks(industry)
    benchmark_terms = []
    for use_case in benchmarks.get("top_use_cases", []):
        title = use_case.get("title", "").strip().lower()
        description = use_case.get("description", "").strip().lower()
        if title:
            benchmark_terms.append(title)
        if description:
            benchmark_terms.extend(
                word for word in description.replace("&", " ").replace("/", " ").replace("-", " ").split()
                if len(word) > 4
            )

    validated = []
    for theme in problem_themes:
        theme_lower = (theme or "").lower()
        theme_words = {
            word for word in theme_lower.replace("&", " ").replace("/", " ").replace("-", " ").split()
            if len(word) > 3
        }
        for term in benchmark_terms:
            term_words = set(term.split())
            if term in theme_lower or len(theme_words.intersection(term_words)) >= 2:
                validated.append(theme)
                break
    return validated
