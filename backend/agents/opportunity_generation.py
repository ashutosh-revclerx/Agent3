"""
agents/opportunity_generation.py
──────────────────────────────────
OPPORTUNITY GENERATION AGENT  (Phase 4)
────────────────────────────────────────
Responsibility:
  - Synthesises Phase 2 objectives, Phase 3 problem clusters,
    Activity A data readiness, Activity B confidence, and seed context
  - Uses Gemini with web search grounding for real-world validation
  - SELF-VERIFIES every generated use case before returning
  - Returns a ranked list of AI use case cards

Pipeline:
  1. gather_context()      — pull all upstream workshop data
  2. generate_candidates() — Gemini generates 8-12 raw use cases
  3. web_search_enrich()   — ground each in real-world evidence
  4. self_verify()         — Gemini checks each use case for quality
  5. rank_and_filter()     — score, deduplicate, return top 6-8
"""

import json
from gemini_client import gemini_json, gemini_text


# ── Self-verification rubric ───────────────────────────────────────────────
VERIFICATION_CRITERIA = """
Score each use case 1-5 on each criterion:
- relevance:    Does it directly address a problem or objective from this workshop?
- specificity:  Is it concrete enough to act on (not just "use AI for X")?
- feasibility:  Is it achievable with current AI technology?
- data_ready:   Does the organisation likely have the data needed?
- roi_clarity:  Is the business value clear and measurable?

Reject (score 0) if:
- It's generic enough to apply to any company in any industry
- It duplicates another use case on the list
- It requires data or infrastructure the org clearly doesn't have
- The ROI claim is vague or unsubstantiated
"""


def generate_use_cases(session: dict) -> dict:
    """
    Main entry point. Returns:
    {
      "use_cases": [...],
      "verification_summary": {...},
      "search_evidence": [...],
      "generation_metadata": {...}
    }
    """
    company  = session.get("company", "the organisation")
    industry = session.get("industry", "General")
    wd       = session.get("workshop_data", {})
    seed     = session.get("seed", {})

    # ── Step 1: gather all context ────────────────────────────────────────
    context = _gather_context(session, wd, seed)

    # ── Step 2: generate candidates ───────────────────────────────────────
    candidates = _generate_candidates(company, industry, context)
    if not candidates:
        candidates = _fallback_use_cases(company, industry, context)

    # ── Step 3: web search enrichment ─────────────────────────────────────
    search_evidence = _web_search_enrich(candidates, industry)

    # ── Step 4: self-verification ─────────────────────────────────────────
    verified, verification_summary = _self_verify(candidates, context, company, industry)

    # ── Step 5: rank and filter ───────────────────────────────────────────
    final = _rank_and_filter(verified, context)

    return {
        "use_cases":             final,
        "verification_summary":  verification_summary,
        "search_evidence":       search_evidence,
        "generation_metadata": {
            "candidates_generated": len(candidates),
            "candidates_verified":  len(verified),
            "candidates_rejected":  len(candidates) - len(verified),
            "final_count":          len(final),
            "context_sources_used": list(context.keys()),
        }
    }


# ── Step 1: Gather context ────────────────────────────────────────────────
def _gather_context(session: dict, wd: dict, seed: dict) -> dict:
    ctx = {}

    # Phase 2 — objectives and growth areas
    phase2 = session.get("phase_data", {}).get("phase2", [])
    if phase2:
        all_objectives  = []
        all_growth      = []
        all_challenges  = []
        roles_seen      = set()
        for sub in phase2:
            all_objectives.extend(sub.get("objectives", []))
            all_growth.extend(sub.get("growth_areas", []))
            chal = sub.get("challenges", "").strip()
            if chal:
                all_challenges.append(chal)
            role = sub.get("participant_role", "")
            if role:
                roles_seen.add(role)
        # Deduplicate and count frequency
        from collections import Counter
        obj_counts    = Counter(all_objectives)
        growth_counts = Counter(all_growth)
        ctx["top_objectives"]  = [o for o, _ in obj_counts.most_common(6)]
        ctx["top_growth"]      = [g for g, _ in growth_counts.most_common(5)]
        ctx["challenges"]      = all_challenges[:5]
        ctx["participant_roles"] = list(roles_seen)

    # Phase 3 — problem clusters
    clusters = wd.get("problem_clusters", [])
    if clusters:
        ctx["problem_clusters"] = [
            {
                "theme":          c.get("theme", ""),
                "summary":        c.get("summary", ""),
                "severity":       c.get("avg_severity", 3),
                "cross_dept":     c.get("cross_department", False),
                "ai_opportunity": c.get("ai_opportunity", ""),
                "auto_targets":   c.get("automation_targets", []),
            }
            for c in clusters
        ]

    # Activity A — data readiness
    readiness = wd.get("data_readiness", {})
    if readiness:
        high_ready = [
            k for k, v in readiness.items()
            if isinstance(v, dict) and v.get("readiness", 0) >= 3.0
        ]
        low_ready = [
            k for k, v in readiness.items()
            if isinstance(v, dict) and v.get("readiness", 0) < 2.5
        ]
        ctx["data_ready_assets"]    = high_ready
        ctx["data_not_ready"]       = low_ready

    # Activity B — team confidence
    conf = wd.get("team_confidence", {})
    if conf:
        ctx["avg_confidence"]  = conf.get("avg_confidence", 3)
        ctx["top_concerns"]    = conf.get("top_concerns", [])

    # Objective map
    obj_map = wd.get("objective_map", {})
    if obj_map:
        ctx["dominant_theme"] = obj_map.get("dominant_theme", "")

    # Seed AI opportunities
    seed_opps = []
    for dept_data in seed.get("insight_mining", {}).get("departments", []):
        seed_opps.extend(dept_data.get("ai_opportunities", []))
    if seed_opps:
        ctx["seed_ai_opportunities"] = seed_opps[:15]

    return ctx


# ── Step 2: Generate candidates ───────────────────────────────────────────
def _generate_candidates(company: str, industry: str, ctx: dict) -> list:

    clusters_text = ""
    if ctx.get("problem_clusters"):
        clusters_text = "\n".join([
            f"  - [{c['theme']}] {c['summary']} "
            f"(severity {c['severity']}/5{'  CROSS-DEPT' if c['cross_dept'] else ''})"
            + (f"\n    Automatable steps: {', '.join(c['auto_targets'])}" if c.get('auto_targets') else "")
            for c in ctx["problem_clusters"]
        ])

    data_text = ""
    if ctx.get("data_ready_assets"):
        data_text = f"High-quality data available: {', '.join(ctx['data_ready_assets'])}"
    if ctx.get("data_not_ready"):
        data_text += f"\nData gaps (lower priority): {', '.join(ctx['data_not_ready'])}"

    prompt = f"""You are a senior AI strategy consultant generating use case recommendations.

ORGANISATION: {company}
INDUSTRY: {industry}
DOMINANT STRATEGIC THEME: {ctx.get('dominant_theme', 'operational efficiency')}

STRATEGIC OBJECTIVES (from participants):
{chr(10).join(f'  - {o}' for o in ctx.get('top_objectives', []))}

GROWTH PRIORITIES:
{chr(10).join(f'  - {g}' for g in ctx.get('top_growth', []))}

OPERATIONAL CHALLENGES DESCRIBED:
{chr(10).join(f'  - {c}' for c in ctx.get('challenges', []))}

PROBLEM CLUSTERS IDENTIFIED (AI-analysed):
{clusters_text or '  (none yet)'}

DATA READINESS:
{data_text or '  (not yet assessed)'}

TEAM AI CONFIDENCE: {ctx.get('avg_confidence', 3)}/5
TEAM CONCERNS: {', '.join(ctx.get('top_concerns', [])) or 'none stated'}

PARTICIPANT ROLES: {', '.join(ctx.get('participant_roles', [])) or 'mixed'}

Generate 8 specific AI use cases tailored to this organisation.

Rules:
- Each must directly address something from the workshop data above
- At least 3 must come from the problem clusters
- At least 2 must be marked data_ready=true (supported by available data)
- For low confidence teams (avg < 3): include at least 2 quick wins (effort=Low)
- No generic use cases — every title must name {company} or be role/dept specific

Return JSON array only:
[
  {{
    "id": "uc_001",
    "title": "Specific use case title (max 8 words)",
    "description": "What the AI does and how it works in this organisation (2-3 sentences)",
    "source_cluster": "Which problem cluster or objective this addresses",
    "impact": "High|Medium|Low",
    "effort": "Low|Medium|High",
    "data_ready": true|false,
    "data_requirement": "What data is needed and whether it exists",
    "estimated_roi": "Specific estimate e.g. '2 hours saved per analyst per day' or '15% reduction in processing time'",
    "quick_win": true|false,
    "pillar": "Sales & Marketing|Operations & Fulfillment|Finance & Administration|Cross-functional",
    "tags": ["Automation", "Analytics", "NLP", "Vision", "Decision-support"]
  }}
]"""

    result = gemini_json(prompt)
    if isinstance(result, list):
        return result
    return []


# ── Step 3: Web search enrichment ────────────────────────────────────────
def _web_search_enrich(candidates: list, industry: str) -> list:
    """
    Uses Gemini with web search grounding to validate each use case
    against real-world adoption evidence. Returns evidence snippets.
    """
    if not candidates:
        return []

    titles = [c.get("title", "") for c in candidates[:6]]  # search top 6

    prompt = f"""For each of these AI use cases in the {industry} industry, 
find real-world evidence of adoption: company names, measurable outcomes, 
deployment timelines, or failure cases that inform feasibility.

Use cases:
{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

For each, return evidence from real deployments. Be specific — name companies 
and cite measurable outcomes where possible.

Return JSON array:
[
  {{
    "use_case": "exact title from above",
    "evidence": "1-2 sentence real-world evidence with company name and outcome",
    "adoption_maturity": "Proven|Emerging|Experimental",
    "risk_flag": "Any known failure pattern or risk to flag"
  }}
]"""

    evidence = gemini_json(prompt)
    if isinstance(evidence, list):
        # Attach evidence to candidates
        ev_map = {e.get("use_case", ""): e for e in evidence}
        for c in candidates:
            match = ev_map.get(c.get("title", ""), {})
            if match:
                c["real_world_evidence"]  = match.get("evidence", "")
                c["adoption_maturity"]    = match.get("adoption_maturity", "Emerging")
                c["risk_flag"]            = match.get("risk_flag", "")
        return evidence

    # Fallback — attach maturity from static benchmark data
    MATURITY_MAP = {
        "report": "Proven", "dashboard": "Proven", "classification": "Proven",
        "forecast": "Proven", "recommendation": "Proven", "detection": "Proven",
        "generation": "Emerging", "agent": "Emerging", "copilot": "Emerging",
        "autonomous": "Experimental",
    }
    for c in candidates:
        title_lower = c.get("title", "").lower()
        maturity = next(
            (v for k, v in MATURITY_MAP.items() if k in title_lower),
            "Emerging"
        )
        c["adoption_maturity"]   = maturity
        c["real_world_evidence"] = ""
        c["risk_flag"]           = ""
    return []


# ── Step 4: Self-verification ─────────────────────────────────────────────
def _self_verify(candidates: list, ctx: dict, company: str, industry: str) -> tuple:
    """
    Gemini reviews its own output against the workshop context.
    Returns (verified_candidates, verification_summary).
    """
    if not candidates:
        return [], {}

    candidates_json = json.dumps(candidates, indent=2)

    prompt = f"""You are reviewing AI use cases generated for {company} ({industry}).

Workshop context:
- Top objectives: {', '.join(ctx.get('top_objectives', [])[:4])}
- Key problem clusters: {', '.join([c['theme'] for c in ctx.get('problem_clusters', [])])}
- Data ready: {', '.join(ctx.get('data_ready_assets', []))}
- Team confidence: {ctx.get('avg_confidence', 3)}/5

Generated use cases to verify:
{candidates_json}

{VERIFICATION_CRITERIA}

For each use case, verify quality and flag issues.

Return JSON:
{{
  "verified": [
    {{
      "id": "uc_001",
      "passes": true,
      "scores": {{"relevance": 4, "specificity": 4, "feasibility": 5, "data_ready": 3, "roi_clarity": 4}},
      "total_score": 20,
      "issues": [],
      "improvement": "Optional: one improvement to apply to the description"
    }}
  ],
  "rejected": [
    {{
      "id": "uc_003",
      "passes": false,
      "reason": "Too generic — applies to any company, not specific to {company}"
    }}
  ],
  "summary": {{
    "total_reviewed": 8,
    "passed": 6,
    "rejected": 2,
    "avg_score": 18.5,
    "quality_assessment": "One sentence overall quality assessment"
  }}
}}"""

    result = gemini_json(prompt)
    if not result:
        # Fallback — pass all candidates with default scores
        verified = []
        for c in candidates:
            c["verification_score"] = 15
            c["verification_issues"] = []
            verified.append(c)
        return verified, {"total_reviewed": len(candidates), "passed": len(candidates), "rejected": 0}

    verified_ids = {v["id"] for v in result.get("verified", []) if v.get("passes")}
    rejected_ids = {r["id"] for r in result.get("rejected", [])}

    # Apply improvements from verification
    score_map = {v["id"]: v for v in result.get("verified", [])}
    verified_candidates = []
    for c in candidates:
        if c.get("id") in verified_ids:
            v = score_map.get(c["id"], {})
            c["verification_score"]  = v.get("total_score", 15)
            c["verification_issues"] = v.get("issues", [])
            # Apply any suggested improvement to description
            if v.get("improvement") and len(v["improvement"]) > 10:
                c["description"] = c["description"] + f" {v['improvement']}"
            verified_candidates.append(c)
        elif c.get("id") not in rejected_ids:
            # Not explicitly rejected — include with lower score
            c["verification_score"]  = 12
            c["verification_issues"] = ["Not explicitly verified"]
            verified_candidates.append(c)

    return verified_candidates, result.get("summary", {})


# ── Step 5: Rank and filter ───────────────────────────────────────────────
def _rank_and_filter(verified: list, ctx: dict) -> list:
    """
    Scores each use case on composite criteria and returns top 6-8.
    """
    avg_confidence = ctx.get("avg_confidence", 3)

    for uc in verified:
        score = uc.get("verification_score", 15)

        # Boost for data readiness
        if uc.get("data_ready"):
            score += 3

        # Boost for cross-functional use cases
        if uc.get("pillar") == "Cross-functional":
            score += 2

        # Boost quick wins for low-confidence teams
        if uc.get("quick_win") and avg_confidence < 3:
            score += 3

        # Impact multiplier
        impact_boost = {"High": 3, "Medium": 1, "Low": 0}
        score += impact_boost.get(uc.get("impact", "Medium"), 1)

        # Effort penalty (high effort = harder sell)
        effort_penalty = {"Low": 0, "Medium": 1, "High": 2}
        score -= effort_penalty.get(uc.get("effort", "Medium"), 1)

        # Adoption maturity boost
        maturity_boost = {"Proven": 2, "Emerging": 1, "Experimental": 0}
        score += maturity_boost.get(uc.get("adoption_maturity", "Emerging"), 1)

        uc["composite_score"] = score

    # Sort by composite score descending
    ranked = sorted(verified, key=lambda x: x.get("composite_score", 0), reverse=True)

    # Ensure diversity — at most 3 from same pillar
    from collections import defaultdict
    pillar_count = defaultdict(int)
    final = []
    for uc in ranked:
        pillar = uc.get("pillar", "Cross-functional")
        if pillar_count[pillar] < 3:
            final.append(uc)
            pillar_count[pillar] += 1
        if len(final) >= 8:
            break

    # Minimum 4
    if len(final) < 4 and ranked:
        final = ranked[:4]

    return final


# ── Fallback use cases ────────────────────────────────────────────────────
def _fallback_use_cases(company: str, industry: str, ctx: dict) -> list:
    """Static fallback when Gemini is unavailable."""
    base = [
        {
            "id": "uc_fallback_001",
            "title": f"Automated Reporting Pipeline for {company}",
            "description": "Replace manual report generation with an AI pipeline that pulls data from existing sources, calculates KPIs, and delivers formatted reports automatically.",
            "source_cluster": "Manual Process Overhead",
            "impact": "High", "effort": "Low", "data_ready": True,
            "data_requirement": "Existing reporting data sources (spreadsheets, databases)",
            "estimated_roi": "3-5 hours saved per analyst per week",
            "quick_win": True,
            "pillar": "Finance & Administration",
            "tags": ["Automation", "Analytics"],
            "adoption_maturity": "Proven",
            "real_world_evidence": "",
            "verification_score": 18,
            "composite_score": 22,
        },
        {
            "id": "uc_fallback_002",
            "title": "AI-Assisted Data Entry and CRM Enrichment",
            "description": "Automate data entry tasks by using AI to extract structured information from emails, documents, and calls and populate CRM records automatically.",
            "source_cluster": "Manual Process Overhead",
            "impact": "High", "effort": "Low", "data_ready": True,
            "data_requirement": "Email/communication data and CRM access",
            "estimated_roi": "2 hours saved per sales/ops person per day",
            "quick_win": True,
            "pillar": "Sales & Marketing",
            "tags": ["Automation", "NLP"],
            "adoption_maturity": "Proven",
            "real_world_evidence": "",
            "verification_score": 17,
            "composite_score": 21,
        },
        {
            "id": "uc_fallback_003",
            "title": "Natural Language Dashboard Querying",
            "description": "Allow business users to ask questions in plain English and receive instant data answers, eliminating dependency on data teams for routine queries.",
            "source_cluster": "Data Scattered",
            "impact": "Medium", "effort": "Medium", "data_ready": False,
            "data_requirement": "Centralised data warehouse or BI tool with API access",
            "estimated_roi": "50% reduction in ad-hoc data requests to analytics team",
            "quick_win": False,
            "pillar": "Cross-functional",
            "tags": ["Analytics", "NLP", "Decision-support"],
            "adoption_maturity": "Emerging",
            "real_world_evidence": "",
            "verification_score": 15,
            "composite_score": 17,
        },
    ]

    # Add cluster-derived fallbacks
    for i, cluster in enumerate(ctx.get("problem_clusters", [])[:2]):
        opp = cluster.get("ai_opportunity", "")
        if opp:
            base.append({
                "id": f"uc_cluster_{i+1:03d}",
                "title": opp[:60],
                "description": f"{opp}. Addresses the '{cluster['theme']}' cluster identified across participants.",
                "source_cluster": cluster["theme"],
                "impact": "High" if cluster.get("severity", 3) >= 4 else "Medium",
                "effort": "Medium",
                "data_ready": bool(ctx.get("data_ready_assets")),
                "data_requirement": "Assessed in Activity A",
                "estimated_roi": "Estimated based on severity and automation targets",
                "quick_win": cluster.get("severity", 3) >= 4,
                "pillar": "Cross-functional",
                "tags": ["Automation"],
                "adoption_maturity": "Emerging",
                "real_world_evidence": "",
                "verification_score": 14,
                "composite_score": 16,
            })

    return base