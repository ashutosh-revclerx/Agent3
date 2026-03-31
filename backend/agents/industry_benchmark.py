"""
agents/industry_benchmark.py
─────────────────────────────
INDUSTRY BENCHMARK AGENT
─────────────────────────
Responsibility:
  - Searches the web via Tavily for real, current AI adoption data per industry
  - Synthesises results with Gemini (google_search grounding tool as backup)
  - Validates which org use cases are sector-proven vs emerging
  - Surfaces hidden opportunities and urgency signals
  - Falls back to curated static data if APIs unavailable

Activated: Phase 0 (preload static) and Phase 6 (live enrichment)
"""
import os, json, re
from gemini_client import gemini_json, get_client
from google.genai import types


# ── Static fallback data ──────────────────────────────────────────────────────
INDUSTRY_BENCHMARKS = {
    "Technology & Software": {
        "adoption_rate": 68,
        "top_use_cases": [
            {"title": "AI Code Review & Generation",     "industry_adoption_pct": 72, "avg_roi": "35%", "complexity": "Medium", "description": "Automated code suggestions, review, and generation using LLMs."},
            {"title": "Automated Customer Support",      "industry_adoption_pct": 61, "avg_roi": "40%", "complexity": "Low",    "description": "AI chatbots handling tier-1 support tickets end-to-end."},
            {"title": "Predictive Sales Forecasting",    "industry_adoption_pct": 54, "avg_roi": "28%", "complexity": "Medium", "description": "ML models predicting pipeline conversion and revenue."},
            {"title": "Intelligent Test Automation",     "industry_adoption_pct": 48, "avg_roi": "25%", "complexity": "Medium", "description": "AI-generated test cases and automated regression coverage."},
            {"title": "AI-Powered Product Analytics",    "industry_adoption_pct": 44, "avg_roi": "30%", "complexity": "High",   "description": "Behavioural analytics and feature adoption insights at scale."},
        ],
        "stat": "Tech companies using AI are shipping 35% faster and cutting support costs by up to 40%.",
    },
    "Financial Services & Banking": {
        "adoption_rate": 71,
        "top_use_cases": [
            {"title": "Fraud Detection & Risk Scoring",  "industry_adoption_pct": 79, "avg_roi": "45%", "complexity": "High",   "description": "Real-time transaction scoring to flag anomalies before they hit."},
            {"title": "AI Document Processing (KYC)",    "industry_adoption_pct": 65, "avg_roi": "30%", "complexity": "Medium", "description": "Automated extraction and verification of identity documents."},
            {"title": "Customer Service Automation",     "industry_adoption_pct": 58, "avg_roi": "35%", "complexity": "Low",    "description": "Conversational AI handling account queries and disputes."},
            {"title": "Credit Risk Assessment",          "industry_adoption_pct": 52, "avg_roi": "40%", "complexity": "High",   "description": "ML-driven credit scoring beyond traditional models."},
            {"title": "Compliance Monitoring",           "industry_adoption_pct": 47, "avg_roi": "20%", "complexity": "High",   "description": "Automated regulatory check and audit trail generation."},
        ],
        "stat": "Financial institutions using AI report 20–30% cost reduction in back-office processes.",
    },
    "Healthcare & Life Sciences": {
        "adoption_rate": 52,
        "top_use_cases": [
            {"title": "Clinical Documentation Automation","industry_adoption_pct": 61, "avg_roi": "40%", "complexity": "Medium", "description": "AI scribes generating clinical notes from patient consultations."},
            {"title": "Patient Triage & Scheduling",     "industry_adoption_pct": 48, "avg_roi": "25%", "complexity": "Medium", "description": "Intelligent prioritisation of patient queues and appointments."},
            {"title": "Medical Coding Automation",       "industry_adoption_pct": 44, "avg_roi": "30%", "complexity": "Low",    "description": "Auto-coding of diagnoses and procedures to reduce billing errors."},
            {"title": "Drug Interaction Checking",       "industry_adoption_pct": 39, "avg_roi": "35%", "complexity": "High",   "description": "AI-powered medication safety checks at point of prescribing."},
            {"title": "Patient Communication AI",        "industry_adoption_pct": 35, "avg_roi": "20%", "complexity": "Low",    "description": "Automated appointment reminders, follow-ups, and FAQs."},
        ],
        "stat": "AI-assisted clinical documentation saves physicians an average of 2 hours per day.",
    },
    "Retail & E-commerce": {
        "adoption_rate": 63,
        "top_use_cases": [
            {"title": "Personalised Product Recommendations","industry_adoption_pct": 74, "avg_roi": "25%", "complexity": "Medium", "description": "Real-time recommendation engines driving basket size uplift."},
            {"title": "Demand Forecasting & Inventory AI",   "industry_adoption_pct": 61, "avg_roi": "30%", "complexity": "Medium", "description": "ML models reducing overstock and stockouts across SKUs."},
            {"title": "AI Customer Support (Chat)",          "industry_adoption_pct": 58, "avg_roi": "35%", "complexity": "Low",    "description": "Conversational AI resolving returns, tracking, and queries."},
            {"title": "Dynamic Pricing Optimisation",        "industry_adoption_pct": 42, "avg_roi": "20%", "complexity": "High",   "description": "Algorithmic pricing reacting to demand, competitor, and inventory signals."},
            {"title": "Visual Search & Catalogue AI",        "industry_adoption_pct": 35, "avg_roi": "15%", "complexity": "High",   "description": "Image-based product search and automated catalogue tagging."},
        ],
        "stat": "Retailers using AI personalisation see 15–25% increase in conversion rates.",
    },
    "Manufacturing & Supply Chain": {
        "adoption_rate": 55,
        "top_use_cases": [
            {"title": "Predictive Maintenance",          "industry_adoption_pct": 67, "avg_roi": "50%", "complexity": "High",   "description": "Sensor-driven ML models predicting equipment failure before it happens."},
            {"title": "Quality Control Vision AI",       "industry_adoption_pct": 54, "avg_roi": "35%", "complexity": "High",   "description": "Computer vision detecting defects on production lines in real time."},
            {"title": "Supply Chain Demand Planning",    "industry_adoption_pct": 49, "avg_roi": "25%", "complexity": "Medium", "description": "AI-driven demand signals reducing lead time and safety stock."},
            {"title": "Worker Safety Monitoring",        "industry_adoption_pct": 38, "avg_roi": "20%", "complexity": "High",   "description": "Vision AI detecting PPE compliance and unsafe behaviours on-site."},
            {"title": "Automated Procurement AI",        "industry_adoption_pct": 32, "avg_roi": "15%", "complexity": "Medium", "description": "AI matching purchase orders, flagging anomalies, and auto-approving within policy."},
        ],
        "stat": "Predictive maintenance alone reduces unplanned downtime by up to 50% in manufacturing.",
    },
    "Professional Services": {
        "adoption_rate": 58,
        "top_use_cases": [
            {"title": "AI Proposal & Report Generation", "industry_adoption_pct": 62, "avg_roi": "40%", "complexity": "Low",    "description": "LLM-drafted proposals and reports from structured briefs."},
            {"title": "Contract Review Automation",      "industry_adoption_pct": 55, "avg_roi": "35%", "complexity": "Medium", "description": "AI flagging risk clauses and summarising contract terms."},
            {"title": "Client Research Automation",      "industry_adoption_pct": 48, "avg_roi": "25%", "complexity": "Low",    "description": "Automated company and market research ahead of client meetings."},
            {"title": "Time & Billing Intelligence",     "industry_adoption_pct": 41, "avg_roi": "20%", "complexity": "Low",    "description": "AI categorising time entries and detecting billing gaps."},
            {"title": "Knowledge Management AI",         "industry_adoption_pct": 37, "avg_roi": "20%", "complexity": "Medium", "description": "Semantic search across internal documents, cases, and templates."},
        ],
        "stat": "Consulting firms using AI for research and drafting reduce delivery time by 30–40%.",
    },
}

DEFAULT_BENCHMARK = {
    "adoption_rate": 48,
    "top_use_cases": [
        {"title": "Process Automation (RPA + AI)",   "industry_adoption_pct": 55, "avg_roi": "30%", "complexity": "Low",    "description": "End-to-end automation of repetitive rule-based workflows."},
        {"title": "AI Customer Support",             "industry_adoption_pct": 49, "avg_roi": "35%", "complexity": "Low",    "description": "Conversational AI handling common customer enquiries 24/7."},
        {"title": "Intelligent Document Processing", "industry_adoption_pct": 44, "avg_roi": "25%", "complexity": "Medium", "description": "AI extracting and classifying data from unstructured documents."},
        {"title": "Predictive Analytics",            "industry_adoption_pct": 38, "avg_roi": "25%", "complexity": "Medium", "description": "ML models forecasting demand, churn, or operational outcomes."},
        {"title": "AI-Assisted Reporting",           "industry_adoption_pct": 32, "avg_roi": "20%", "complexity": "Low",    "description": "Automated narrative and visual report generation from raw data."},
    ],
    "stat": "Organisations deploying AI in operations report average productivity gains of 20–30%.",
}


# ── Tavily web search ─────────────────────────────────────────────────────────

def _tavily_search(queries: list) -> str:
    """
    Runs multiple Tavily searches and concatenates the best snippets.
    Returns empty string if TAVILY_API_KEY is not set or search fails.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("⚠️  TAVILY_API_KEY not set — skipping live web search for benchmark")
        return ""

    try:
        import httpx
        snippets = []

        for query in queries:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key":             api_key,
                    "query":               query,
                    "search_depth":        "advanced",
                    "include_answer":      True,
                    "include_raw_content": False,
                    "max_results":         4,
                },
                timeout=12,
            )
            if resp.status_code != 200:
                print(f"Tavily non-200 for '{query}': {resp.status_code}")
                continue

            data = resp.json()

            # Tavily synthesised answer is highest quality — use it first
            if data.get("answer"):
                snippets.append(f"[Query: {query}]\nAnswer: {data['answer']}")

            # Individual result snippets (truncated)
            for r in data.get("results", [])[:3]:
                content = r.get("content", "").strip()
                if content:
                    snippets.append(f"Source: {r.get('url', 'unknown')}\n{content[:500]}")

        return "\n\n---\n\n".join(snippets)

    except Exception as e:
        print(f"Tavily search error: {e}")
        return ""


# ── Gemini with google_search grounding tool ──────────────────────────────────

def _gemini_with_web_grounding(prompt: str) -> dict | None:
    """
    Calls Gemini with google_search grounding enabled so it can fetch
    live web data directly. Falls back to plain gemini_json if unavailable.
    """
    client = get_client()
    if not client:
        return None

    # Try with google_search grounding first
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = (response.text or "").strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$',          '', text).strip()
        if text:
            return json.loads(text)
    except Exception as e:
        print(f"Gemini google_search grounding error: {e} — trying plain Gemini")

    # Fallback: plain Gemini without web tool
    return gemini_json(prompt)


# ── Main Phase 6 enrichment ───────────────────────────────────────────────────

def enrich_with_gemini(industry: str, company: str, org_use_cases: list) -> dict:
    """
    Phase 6 live enrichment pipeline:
      1. Tavily searches for real current AI adoption data in this industry
      2. Feeds results to Gemini (with google_search grounding as a second live layer)
      3. Returns a fully structured benchmark object for the frontend
    """
    static = get_industry_benchmarks(industry)

    # Step 1 — Tavily live web search
    tavily_context = _tavily_search([
        f"AI adoption statistics {industry}  2025 2026",
        f"top AI use cases {industry} companies deploying now",
        f"AI ROI return on investment {industry} industry 2025  report",
    ])

    web_section = (
        f"\n\nLive web research retrieved via Tavily:\n{tavily_context[:3500]}"
        if tavily_context
        else "\n\n(No Tavily data — use your own knowledge for current statistics.)"
    )

    org_titles  = ", ".join(org_use_cases[:6]) if org_use_cases else "none yet"
    static_ucs  = json.dumps(static["top_use_cases"], indent=2)

    # Step 2 — Gemini synthesis prompt
    prompt = f"""You are an AI strategy analyst delivering live industry benchmark data in a consulting workshop.

Company: {company}
Industry: {industry}
Organisation's proposed AI use cases: {org_titles}

Baseline static data (use as a floor — override with live data where better):
- Adoption rate: {static['adoption_rate']}%
- Key stat: {static['stat']}
- Top use cases baseline:
{static_ucs}
{web_section}

Using the best available data (live Tavily data preferred over static baseline),
return a JSON object with this exact structure:
{{
  "adoption_rate": <integer 0-100>,
  "headline": "One striking, specific sentence about AI momentum in {industry} right now — cite a real number",
  "stat": "One concrete statistic with a number (e.g. '68% of {industry} firms now run at least one AI system in production')",
  "top_use_cases": [
    {{
      "title": "Use case name",
      "description": "One sentence: what this does in practice",
      "industry_adoption_pct": <integer 0-100>,
      "avg_roi": "e.g. 30%",
      "complexity": "Low|Medium|High"
    }}
  ],
  "org_alignment": "One sentence: how well {company}'s proposed use cases align with what the industry is actually deploying",
  "hidden_opportunity": "One specific, named use case widely deployed in {industry} that {company} has NOT mentioned — be concrete",
  "urgency_signal": "One factual, specific sentence on what happens to {industry} companies that delay AI — cite a consequence or stat"
}}

Rules:
- top_use_cases: exactly 5, ranked by industry_adoption_pct descending
- Prefer real numbers from the web data; estimate from static if needed
- hidden_opportunity must NOT be any of: {org_titles}
- Return ONLY valid JSON, no markdown, no preamble"""

    # Step 3 — Gemini with google_search grounding (second live layer)
    result = _gemini_with_web_grounding(prompt)

    if result and isinstance(result, dict) and "top_use_cases" in result:
        # Normalise adoption_rate to int
        try:
            result["adoption_rate"] = int(
                str(result.get("adoption_rate", static["adoption_rate"]))
                .replace("%", "").strip()
            )
        except (ValueError, TypeError):
            result["adoption_rate"] = static["adoption_rate"]
        print(f"✅ Benchmark enriched with live data for {industry} (adoption: {result['adoption_rate']}%)")
        return result

    # Step 4 — Pure static fallback
    print(f"⚠️  Benchmark: all live sources failed — using static data for {industry}")
    return {
        **static,
        "headline": (
            f"{static['adoption_rate']}% of {industry} companies are actively deploying AI — "
            f"the window for first-mover advantage is closing fast."
        ),
        "org_alignment": (
            f"{company}'s priorities closely mirror what leading {industry} companies are already deploying."
        ),
        "hidden_opportunity": (
            static["top_use_cases"][2]["title"]
            if len(static["top_use_cases"]) > 2
            else "Intelligent Document Processing"
        ),
        "urgency_signal": (
            f"Companies that started AI pilots in 2023–24 are already reporting measurable ROI — "
            f"late movers in {industry} face a 2–3 year capability gap."
        ),
    }


# ── Phase 0 preload (fast, no web search) ────────────────────────────────────

def get_industry_benchmarks(industry: str) -> dict:
    """
    Returns static benchmark data. Called at session creation (Phase 0)
    so baseline data is immediately available without incurring web search latency.
    Full live enrichment happens at Phase 6 via enrich_with_gemini().
    """
    industry_lower = industry.lower()
    for key, data in INDUSTRY_BENCHMARKS.items():
        if any(word in industry_lower for word in key.lower().split(" & ")):
            return data
    return DEFAULT_BENCHMARK


# ── Cross-reference org use cases ────────────────────────────────────────────

def cross_reference_org_use_cases(org_use_cases: list, industry: str) -> list:
    """
    Tags each org use case with sector_validated, industry_adoption_pct, and avg_roi
    based on fuzzy keyword matching against the benchmark top use cases.
    """
    benchmarks  = get_industry_benchmarks(industry)
    benchmark_map = {uc["title"].lower(): uc for uc in benchmarks["top_use_cases"]}

    enriched = []
    for uc in org_use_cases:
        match     = None
        uc_words  = set(uc.get("title", "").lower().split())
        for bt, bdata in benchmark_map.items():
            if len(uc_words & set(bt.split())) >= 2:
                match = bdata
                break
        enriched.append({
            **uc,
            "sector_validated":      match is not None,
            "industry_adoption_pct": match.get("industry_adoption_pct", 0) if match else 0,
            "avg_roi":               match.get("avg_roi") if match else None,
        })
    return enriched