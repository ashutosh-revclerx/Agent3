"""
agents/prioritisation_roi.py
─────────────────────────────
PRIORITISATION AND ROI AGENT
─────────────────────────────
Responsibility:
  - Evaluates use cases on impact, feasibility, data readiness, and estimated value
  - Places use cases in the Impact vs Effort matrix
  - Categorises into: Quick Wins / Strategic Projects / Long-term Innovations
  - Estimates ROI and implementation timeline
  - Triggers Agent Builder scaffold for the top-voted use case

Activated: Phase 8 — after Poll 2 results are revealed
"""
from gemini_client import gemini_json
from typing import List


# ── Matrix quadrant definitions ───────────────────────────────────────────────
QUADRANTS = {
    "quick_win":   {"label": "Quick Win",            "desc": "High impact, low effort — start now"},
    "strategic":   {"label": "Strategic Project",    "desc": "High impact, high effort — plan and resource"},
    "fill_in":     {"label": "Fill-in",              "desc": "Low impact, low effort — nice to have"},
    "deprioritise":{"label": "Deprioritise",         "desc": "Low impact, high effort — avoid for now"},
}

EFFORT_BUCKETS = {
    "Low":    {"weeks": "2–6 weeks",  "cost_range": "$5k–$20k",   "effort_score": 1},
    "Medium": {"weeks": "2–4 months", "cost_range": "$20k–$80k",  "effort_score": 2},
    "High":   {"weeks": "4–12 months","cost_range": "$80k–$300k+","effort_score": 3},
}

IMPACT_LEVELS = {
    "High":   {"score": 3, "desc": "Significant revenue, cost, or experience improvement"},
    "Medium": {"score": 2, "desc": "Moderate improvement, clear but not transformational"},
    "Low":    {"score": 1, "desc": "Minor efficiency gain"},
}


def score_use_cases(use_cases: list, data_readiness_map: dict,
                    company: str, industry: str) -> list:
    """
    Scores each use case and places it in the Impact vs Effort matrix.

    use_cases: list of { id, title, description, vote_count, sector_validated }
    data_readiness_map: { dataset_id: avg_score } from Activity A
    """
    if not use_cases:
        return []

    uc_text = "\n".join([
        f"- {uc.get('title', '')}: {uc.get('description', '')} "
        f"(votes: {uc.get('vote_count', 0)}, "
        f"sector_validated: {uc.get('sector_validated', False)})"
        for uc in use_cases
    ])

    dr_text = (
        "Data available: " + ", ".join([f"{k}: {v:.1f}/4" for k, v in data_readiness_map.items()])
        if data_readiness_map else "Data readiness: unknown"
    )

    prompt = f"""You are evaluating AI use cases for {company} ({industry}).

Use cases to evaluate:
{uc_text}

{dr_text}

For each use case, return a JSON array:
[
  {{
    "id": "same id as input",
    "title": "same title",
    "impact": "High|Medium|Low",
    "effort": "Low|Medium|High",
    "quadrant": "quick_win|strategic|fill_in|deprioritise",
    "data_ready": true/false,
    "estimated_roi": "e.g. 30% reduction in processing time",
    "timeline": "e.g. 6–8 weeks",
    "why": "One sentence: why this quadrant placement"
  }}
]

Rules:
- quick_win = High impact + Low effort
- strategic = High impact + High/Medium effort
- fill_in   = Low/Medium impact + Low effort
- deprioritise = Low impact + High effort
- data_ready = true if the required data scores >= 2.5/4
Return ONLY the JSON array."""

    result = gemini_json(prompt)
    if result and isinstance(result, list):
        # Merge back with original use case data
        scored_map = {r["id"]: r for r in result if "id" in r}
        return [
            {**uc, **scored_map.get(uc.get("id", ""), {})}
            for uc in use_cases
        ]

    # ── Fallback: rule-based scoring ──
    scored = []
    for i, uc in enumerate(use_cases):
        votes = uc.get("vote_count", 0)
        validated = uc.get("sector_validated", False)
        impact = "High" if votes >= 3 or validated else "Medium" if votes >= 1 else "Low"
        # Simple effort heuristic based on title keywords
        title_lower = uc.get("title", "").lower()
        if any(w in title_lower for w in ["report", "summarise", "draft", "classify", "sort"]):
            effort = "Low"
        elif any(w in title_lower for w in ["predict", "forecast", "integrate", "train"]):
            effort = "High"
        else:
            effort = "Medium"

        impact_score = IMPACT_LEVELS[impact]["score"]
        effort_score = EFFORT_BUCKETS[effort]["effort_score"]

        if impact_score >= 3 and effort_score <= 1:
            quadrant = "quick_win"
        elif impact_score >= 2 and effort_score >= 2:
            quadrant = "strategic"
        elif impact_score <= 1 and effort_score <= 1:
            quadrant = "fill_in"
        else:
            quadrant = "deprioritise"

        scored.append({
            **uc,
            "impact":       impact,
            "effort":       effort,
            "quadrant":     quadrant,
            "data_ready":   True,
            "estimated_roi": "15–30% efficiency improvement",
            "timeline":     EFFORT_BUCKETS[effort]["weeks"],
            "why":          f"{'High participant demand and' if votes >= 3 else ''} {impact.lower()} impact potential with {effort.lower()} implementation complexity.",
        })
    return scored


def build_matrix(scored_use_cases: list) -> dict:
    """
    Organises scored use cases into the 4 matrix quadrants.
    Returns the full Impact vs Effort matrix structure.
    """
    matrix = {q: [] for q in QUADRANTS}
    for uc in scored_use_cases:
        q = uc.get("quadrant", "fill_in")
        if q in matrix:
            matrix[q].append(uc)

    # Sort each quadrant by vote count descending
    for q in matrix:
        matrix[q].sort(key=lambda x: x.get("vote_count", 0), reverse=True)

    return {
        "quadrants": matrix,
        "quadrant_labels": QUADRANTS,
        "top_recommendation": scored_use_cases[0] if scored_use_cases else None,
    }


def generate_roi_summary(company: str, matrix: dict) -> str:
    """
    Generates a 2-sentence ROI summary for the prioritisation results.
    """
    quick_wins = matrix["quadrants"].get("quick_win", [])
    strategic  = matrix["quadrants"].get("strategic", [])

    prompt = (
        f"Summarise the AI prioritisation results for {company}. "
        f"Quick wins: {[uc['title'] for uc in quick_wins[:2]]}. "
        f"Strategic projects: {[uc['title'] for uc in strategic[:2]]}. "
        f"Write 2 sentences: what should they do first and why. Be direct and specific."
    )

    result = gemini_json(prompt)
    if isinstance(result, str):
        return result

    if quick_wins:
        return (
            f"Start with {quick_wins[0]['title']} — it's high impact and can be live within "
            f"{quick_wins[0].get('timeline', '6–8 weeks')}. "
            f"{'Meanwhile, resource planning for ' + strategic[0]['title'] + ' should begin in parallel.' if strategic else ''}"
        )
    return f"{company} has identified {len(scored := matrix['quadrants'].get('strategic', []))} strategic AI initiatives. Begin with a focused proof-of-concept before committing to full implementation."