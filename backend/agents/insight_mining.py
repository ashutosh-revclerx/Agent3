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


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Business Objective Map
# ─────────────────────────────────────────────────────────────────────────────
def build_objective_map(company: str, industry: str, objectives: list,
                        growth_areas: list, challenges: str) -> dict:
    """
    Analyses strategic objectives, growth priorities, and challenge text.
    Returns a business objective map with themed clusters.
    """
    prompt = f"""You are an AI strategy analyst in a live consulting workshop.

Organisation: {company}
Industry: {industry}
Strategic objectives selected: {', '.join(objectives)}
Growth priorities: {', '.join(growth_areas)}
Operational challenges described: {challenges}

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

    # ── Fallback ──
    clusters = []
    if any(o in objectives for o in ['revenue', 'cx', 'scale']):
        clusters.append({
            "icon": "◆", "theme": "Growth & Customer Intelligence",
            "signals": 2,
            "summary": f"{company} is prioritising revenue expansion and customer experience. Growth is the dominant strategic driver.",
            "ai_potential": "AI-powered customer segmentation and personalised engagement automation"
        })
    if any(o in objectives for o in ['efficiency', 'talent', 'data']):
        clusters.append({
            "icon": "◈", "theme": "Operational Efficiency",
            "signals": 3,
            "summary": "Manual processes and data silos are limiting productivity. Teams are spending time on work that AI can automate.",
            "ai_potential": "Intelligent workflow automation with real-time performance dashboards"
        })
    if not clusters:
        clusters.append({
            "icon": "◎", "theme": "Strategic AI Readiness",
            "signals": 1,
            "summary": f"{company} is beginning to map where AI can create most value. This workshop will build that clarity.",
            "ai_potential": "Targeted AI pilots in highest-friction workflows identified today"
        })
    return {
        "dominant_theme": f"{company} is focused on {objectives[0] if objectives else 'operational improvement'} as its primary strategic driver.",
        "clusters": clusters
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Problem Clustering
# ─────────────────────────────────────────────────────────────────────────────
def cluster_problems(company: str, industry: str, problems: list) -> list:
    """
    Takes a list of submitted problems and clusters them into strategic themes.
    Detects cross-department patterns and assigns AI opportunities.

    problems: list of dicts with keys: text, tags, severity, department
    """
    if not problems:
        return []

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
        clusters.append({
            "icon": "◈", "theme": "Manual Process Overhead",
            "problem_count": len(manual),
            "summary": "Teams are spending significant time on repetitive manual tasks. This work is directly automatable with AI.",
            "departments": departments[:3], "cross_department": len(departments) > 1,
            "avg_severity": round(avg_sev, 1),
            "ai_opportunity": "RPA + AI workflow agents to eliminate manual data entry and repetitive processing"
        })
    if time_cons:
        clusters.append({
            "icon": "◆", "theme": "Slow Decisions & Reporting",
            "problem_count": len(time_cons),
            "summary": "Reporting and decision workflows are too slow. Real-time AI analytics would eliminate the lag.",
            "departments": departments[:2], "cross_department": len(departments) > 1,
            "avg_severity": round(min(avg_sev + 0.3, 5.0), 1),
            "ai_opportunity": "AI reporting pipeline with natural language querying and automated alerts"
        })
    if not clusters:
        clusters.append({
            "icon": "◎", "theme": "Operational Friction Points",
            "problem_count": len(problems),
            "summary": f"{company} has identified several high-priority areas for AI automation. These represent the best starting points.",
            "departments": departments, "cross_department": len(departments) > 1,
            "avg_severity": round(avg_sev, 1),
            "ai_opportunity": "Targeted AI pilots in the workflows with the highest severity scores"
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
    # TODO: connect to industry benchmark database in Phase 6
    # For now, return a simple signal map
    COMMON_BY_INDUSTRY = {
        "Technology & Software":         ["manual reporting", "lead qualification", "support tickets"],
        "Financial Services & Banking":  ["document processing", "compliance checks", "customer onboarding"],
        "Healthcare & Life Sciences":    ["patient data entry", "appointment scheduling", "billing"],
        "Retail & E-commerce":           ["inventory management", "customer support", "demand forecasting"],
        "Manufacturing & Supply Chain":  ["quality control", "predictive maintenance", "inventory"],
        "Professional Services":         ["time tracking", "proposal generation", "client reporting"],
    }
    common = COMMON_BY_INDUSTRY.get(industry, [])
    validated = []
    for theme in problem_themes:
        for c in common:
            if c.lower() in theme.lower():
                validated.append(theme)
                break
    return validated