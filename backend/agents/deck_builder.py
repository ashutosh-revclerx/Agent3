"""
agents/deck_builder.py
───────────────────────
DECK BUILDER AGENT
──────────────────
Responsibility:
  - Transforms all workshop outputs into structured deliverables
  - Generates: strategy deck content, roadmap, use case list, readiness report
  - Produces the full session summary for PDF/PPTX/Google Doc export
  - Activated exclusively in Phase 11

Activated: Phase 11 — after all phases are complete
"""
from gemini_client import gemini_json, gemini_text
from typing import Optional


# ── Slide templates ───────────────────────────────────────────────────────────
SLIDE_STRUCTURE = [
    {"id": "cover",       "title": "Cover",                  "type": "cover"},
    {"id": "agenda",      "title": "Workshop Overview",       "type": "agenda"},
    {"id": "context",     "title": "Strategic Context",       "type": "objective_map"},
    {"id": "problems",    "title": "Operational Challenges",  "type": "problem_clusters"},
    {"id": "readiness",   "title": "AI Readiness Assessment", "type": "readiness"},
    {"id": "use_cases",   "title": "AI Opportunities",        "type": "use_case_list"},
    {"id": "matrix",      "title": "Impact vs Effort Matrix", "type": "matrix"},
    {"id": "roadmap",     "title": "Implementation Roadmap",  "type": "roadmap"},
    {"id": "next_steps",  "title": "Recommended Next Steps",  "type": "next_steps"},
]


def build_deck_content(session: dict, workshop_data: dict) -> dict:
    """
    Assembles all workshop outputs into structured deck content.
    Each slide has a title, bullet points, and optional visual data.

    session:       the session dict (company, industry, etc.)
    workshop_data: all collected phase data:
      {
        objective_map, problem_clusters, data_readiness,
        confidence_profile, use_cases, poll_results,
        matrix, roadmap, readiness_score
      }
    """
    company  = session.get("company", "Your Organisation")
    industry = session.get("industry", "")

    slides = []

    # ── Slide 1: Cover ──
    slides.append({
        "id":       "cover",
        "title":    f"AI Strategy Discovery — {company}",
        "subtitle": f"Workshop Report | {industry}",
        "type":     "cover",
    })

    # ── Slide 2: Dominant theme ──
    obj_map = workshop_data.get("objective_map", {})
    slides.append({
        "id":      "context",
        "title":   "Strategic Context",
        "headline": obj_map.get("dominant_theme", ""),
        "bullets": [c.get("theme") + ": " + c.get("summary", "")
                    for c in obj_map.get("clusters", [])],
        "type":    "objective_map",
    })

    # ── Slide 3: Problem clusters ──
    clusters = workshop_data.get("problem_clusters", [])
    slides.append({
        "id":      "problems",
        "title":   "Operational Challenges Identified",
        "bullets": [f"{c.get('theme')}: {c.get('summary', '')}" for c in clusters],
        "insight": f"{len(clusters)} strategic themes identified across departments.",
        "type":    "problem_clusters",
    })

    # ── Slide 4: Use case list ──
    use_cases = workshop_data.get("use_cases", [])
    matrix    = workshop_data.get("matrix", {})
    quick_wins = matrix.get("quadrants", {}).get("quick_win", [])
    strategic  = matrix.get("quadrants", {}).get("strategic", [])
    slides.append({
        "id":         "use_cases",
        "title":      "AI Opportunities — Prioritised",
        "quick_wins": [{"title": uc.get("title"), "timeline": uc.get("timeline")} for uc in quick_wins[:3]],
        "strategic":  [{"title": uc.get("title"), "timeline": uc.get("timeline")} for uc in strategic[:3]],
        "type":       "use_case_list",
    })

    # ── Slide 5: Roadmap ──
    roadmap = workshop_data.get("roadmap", {})
    slides.append({
        "id":    "roadmap",
        "title": "Implementation Roadmap",
        "phases": roadmap.get("phases", []),
        "type":  "roadmap",
    })

    # ── Slide 6: Readiness ──
    readiness = workshop_data.get("readiness_score", {})
    slides.append({
        "id":     "readiness",
        "title":  "AI Readiness Assessment",
        "score":  readiness.get("overall_score", 0),
        "label":  readiness.get("label", ""),
        "dims":   readiness.get("dimensions", []),
        "type":   "readiness",
    })

    # ── Slide 7: Next steps ──
    next_steps = generate_next_steps(company, quick_wins, strategic)
    slides.append({
        "id":     "next_steps",
        "title":  "Recommended Next Steps",
        "steps":  next_steps,
        "type":   "next_steps",
    })

    return {
        "company":   company,
        "industry":  industry,
        "slides":    slides,
        "slide_count": len(slides),
    }


def generate_roadmap(company: str, industry: str,
                     quick_wins: list, strategic: list,
                     readiness_score: float) -> dict:
    """
    Generates the 3-phase implementation roadmap.
    Phase 1 = Quick Wins, Phase 2 = Operational Transformation, Phase 3 = Advanced AI
    """
    prompt = f"""Create a 3-phase AI implementation roadmap for {company} ({industry}).

Quick wins to start with: {[uc.get('title') for uc in quick_wins[:3]]}
Strategic projects: {[uc.get('title') for uc in strategic[:3]]}
AI readiness score: {readiness_score:.1f}/10

Return JSON:
{{
  "phases": [
    {{
      "number": 1,
      "label": "Quick Wins",
      "timeframe": "0–3 months",
      "description": "What gets done and why now",
      "initiatives": ["use case title", "use case title"],
      "success_metric": "How to measure success"
    }},
    {{
      "number": 2,
      "label": "Operational Transformation",
      "timeframe": "3–9 months",
      "description": "Core workflow integration",
      "initiatives": ["..."],
      "success_metric": "..."
    }},
    {{
      "number": 3,
      "label": "Advanced Intelligence",
      "timeframe": "9–18 months",
      "description": "Predictive and strategic AI systems",
      "initiatives": ["..."],
      "success_metric": "..."
    }}
  ],
  "summary": "2-sentence strategic narrative for this roadmap"
}}"""

    result = gemini_json(prompt)
    if result:
        return result

    # ── Fallback ──
    return {
        "phases": [
            {
                "number": 1, "label": "Quick Wins", "timeframe": "0–3 months",
                "description": "Deploy high-impact, low-complexity AI tools that deliver immediate ROI.",
                "initiatives": [uc.get("title", "") for uc in quick_wins[:2]],
                "success_metric": "Time savings measurable within 30 days of deployment.",
            },
            {
                "number": 2, "label": "Operational Transformation", "timeframe": "3–9 months",
                "description": "Integrate AI into core workflows. Requires data preparation and change management.",
                "initiatives": [uc.get("title", "") for uc in strategic[:2]],
                "success_metric": "20%+ reduction in process time or error rate.",
            },
            {
                "number": 3, "label": "Advanced Intelligence", "timeframe": "9–18 months",
                "description": "Predictive analytics, autonomous decision systems, and strategic AI capabilities.",
                "initiatives": ["Predictive Analytics Platform", "AI-Driven Strategic Planning"],
                "success_metric": "Revenue or cost impact measurable at the P&L level.",
            },
        ],
        "summary": (
            f"{company}'s roadmap prioritises quick ROI in the first 90 days, "
            f"followed by systematic operational transformation. "
            f"By month 18, AI will be embedded in core business processes."
        ),
    }


def generate_next_steps(company: str, quick_wins: list, strategic: list) -> list:
    """Returns a concrete list of next steps the organisation should take."""
    steps = [
        f"Appoint an AI project lead for the {quick_wins[0].get('title', 'first quick win')} initiative" if quick_wins else "Appoint an internal AI project lead",
        "Run a 2-week data audit to confirm readiness for top use cases",
        f"Request vendor demos for {quick_wins[0].get('title', 'priority use case')} solutions" if quick_wins else "Begin vendor evaluation process",
        "Define success metrics and baseline measurements before any AI deployment",
        "Share this report with your leadership team and align on Phase 1 budget",
    ]
    if strategic:
        steps.append(f"Begin stakeholder alignment for {strategic[0].get('title', 'strategic project')} (Phase 2)")
    return steps


def generate_executive_summary(session: dict, workshop_data: dict) -> str:
    """
    Generates a 3-paragraph executive summary of the entire workshop.
    Used as the opening of the PDF report.
    """
    company  = session.get("company", "The organisation")
    industry = session.get("industry", "")
    n_participants = len(session.get("participants", []))
    obj_map  = workshop_data.get("objective_map", {})
    clusters = workshop_data.get("problem_clusters", [])
    matrix   = workshop_data.get("matrix", {})
    qw       = matrix.get("quadrants", {}).get("quick_win", [])

    prompt = (
        f"Write a 3-paragraph executive summary of an AI strategy workshop.\n\n"
        f"Company: {company} | Industry: {industry} | Participants: {n_participants}\n"
        f"Dominant strategic theme: {obj_map.get('dominant_theme', '')}\n"
        f"Top problem clusters: {[c.get('theme') for c in clusters[:3]]}\n"
        f"Quick win opportunities: {[uc.get('title') for uc in qw[:3]]}\n\n"
        f"Paragraph 1: Why this workshop was conducted and who attended.\n"
        f"Paragraph 2: What the team discovered — key themes and problems.\n"
        f"Paragraph 3: What the recommended path forward is.\n"
        f"Tone: confident, strategic, consulting-grade. No bullet points."
    )

    result = gemini_text(prompt)
    if result:
        return result

    return (
        f"{company} conducted an AI strategy discovery workshop with {n_participants} participants "
        f"across multiple departments to identify where artificial intelligence can create the most "
        f"immediate and strategic value.\n\n"
        f"The session surfaced {len(clusters)} strategic problem clusters, with "
        f"{obj_map.get('dominant_theme', 'operational efficiency')} emerging as the dominant theme. "
        f"Participants identified {len(qw)} quick-win AI opportunities that can be implemented within 90 days.\n\n"
        f"The recommended path forward begins with {qw[0].get('title', 'process automation') if qw else 'targeted AI pilots'}, "
        f"followed by a structured operational transformation programme. "
        f"This report provides the full roadmap, readiness assessment, and prioritised use case list."
    )