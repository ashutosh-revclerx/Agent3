"""
agents/industry_benchmark.py
─────────────────────────────
INDUSTRY BENCHMARK AGENT
─────────────────────────
Responsibility:
  - Provides contextual recommendations based on industry AI adoption trends
  - Surfaces which use cases are widely adopted globally
  - Shows which have demonstrated high ROI
  - Powers Phase 6 — the global adoption insight / education window
  - Pre-loaded before the session starts (Phase 0)

Activated: Phase 0 (preload) and Phase 6 (reveal to participants)

Data source: Static industry knowledge + Gemini for dynamic enrichment
             (Future: live web scraping + competitor AI audits)
"""
from gemini_client import gemini_json

# ── Static industry AI adoption data ──────────────────────────────────────────
# Source: synthesised from McKinsey, Gartner, CB Insights AI adoption reports
INDUSTRY_BENCHMARKS = {
    "Technology & Software": {
        "adoption_rate": "68%",
        "top_use_cases": [
            {"title": "AI Code Review & Generation",     "adoption": "72%", "roi": "High",   "complexity": "Medium"},
            {"title": "Automated Customer Support",      "adoption": "61%", "roi": "High",   "complexity": "Low"},
            {"title": "Predictive Sales Forecasting",    "adoption": "54%", "roi": "High",   "complexity": "Medium"},
            {"title": "Intelligent Test Automation",     "adoption": "48%", "roi": "Medium", "complexity": "Medium"},
            {"title": "AI-Powered Product Analytics",    "adoption": "44%", "roi": "High",   "complexity": "High"},
        ],
        "stat": "Tech companies using AI are shipping 35% faster and cutting support costs by up to 40%.",
    },
    "Financial Services & Banking": {
        "adoption_rate": "71%",
        "top_use_cases": [
            {"title": "Fraud Detection & Risk Scoring",  "adoption": "79%", "roi": "High",   "complexity": "High"},
            {"title": "AI Document Processing (KYC)",    "adoption": "65%", "roi": "High",   "complexity": "Medium"},
            {"title": "Customer Service Automation",     "adoption": "58%", "roi": "High",   "complexity": "Low"},
            {"title": "Credit Risk Assessment",          "adoption": "52%", "roi": "High",   "complexity": "High"},
            {"title": "Compliance Monitoring",           "adoption": "47%", "roi": "Medium", "complexity": "High"},
        ],
        "stat": "Financial institutions using AI in operations report 20–30% cost reduction in back-office processes.",
    },
    "Healthcare & Life Sciences": {
        "adoption_rate": "52%",
        "top_use_cases": [
            {"title": "Clinical Documentation Automation","adoption": "61%", "roi": "High",   "complexity": "Medium"},
            {"title": "Patient Triage & Scheduling",     "adoption": "48%", "roi": "High",   "complexity": "Medium"},
            {"title": "Medical Coding Automation",       "adoption": "44%", "roi": "High",   "complexity": "Low"},
            {"title": "Drug Interaction Checking",       "adoption": "39%", "roi": "High",   "complexity": "High"},
            {"title": "Patient Communication AI",        "adoption": "35%", "roi": "Medium", "complexity": "Low"},
        ],
        "stat": "AI-assisted clinical documentation saves physicians an average of 2 hours per day.",
    },
    "Retail & E-commerce": {
        "adoption_rate": "63%",
        "top_use_cases": [
            {"title": "Personalised Product Recommendations","adoption": "74%","roi": "High",  "complexity": "Medium"},
            {"title": "Demand Forecasting & Inventory AI",   "adoption": "61%","roi": "High",  "complexity": "Medium"},
            {"title": "AI Customer Support (Chat)",          "adoption": "58%","roi": "High",  "complexity": "Low"},
            {"title": "Dynamic Pricing Optimisation",        "adoption": "42%","roi": "High",  "complexity": "High"},
            {"title": "Visual Search & Catalogue AI",        "adoption": "35%","roi": "Medium","complexity": "High"},
        ],
        "stat": "Retailers using AI personalisation see 15–25% increase in conversion rates.",
    },
    "Manufacturing & Supply Chain": {
        "adoption_rate": "55%",
        "top_use_cases": [
            {"title": "Predictive Maintenance",          "adoption": "67%", "roi": "High",   "complexity": "High"},
            {"title": "Quality Control Vision AI",       "adoption": "54%", "roi": "High",   "complexity": "High"},
            {"title": "Supply Chain Demand Planning",    "adoption": "49%", "roi": "High",   "complexity": "Medium"},
            {"title": "Worker Safety Monitoring",        "adoption": "38%", "roi": "Medium", "complexity": "High"},
            {"title": "Automated Procurement AI",        "adoption": "32%", "roi": "Medium", "complexity": "Medium"},
        ],
        "stat": "Predictive maintenance alone reduces unplanned downtime by up to 50% in manufacturing.",
    },
    "Professional Services & Consulting": {
        "adoption_rate": "58%",
        "top_use_cases": [
            {"title": "AI Proposal & Report Generation", "adoption": "62%", "roi": "High",   "complexity": "Low"},
            {"title": "Contract Review Automation",      "adoption": "55%", "roi": "High",   "complexity": "Medium"},
            {"title": "Client Research Automation",      "adoption": "48%", "roi": "Medium", "complexity": "Low"},
            {"title": "Time & Billing Intelligence",     "adoption": "41%", "roi": "Medium", "complexity": "Low"},
            {"title": "Knowledge Management AI",         "adoption": "37%", "roi": "Medium", "complexity": "Medium"},
        ],
        "stat": "Consulting firms using AI for research and drafting reduce delivery time by 30–40%.",
    },
}

DEFAULT_BENCHMARK = {
    "adoption_rate": "48%",
    "top_use_cases": [
        {"title": "Process Automation (RPA + AI)",   "adoption": "55%", "roi": "High",   "complexity": "Low"},
        {"title": "AI Customer Support",             "adoption": "49%", "roi": "High",   "complexity": "Low"},
        {"title": "Intelligent Document Processing", "adoption": "44%", "roi": "High",   "complexity": "Medium"},
        {"title": "Predictive Analytics",            "adoption": "38%", "roi": "High",   "complexity": "Medium"},
        {"title": "AI-Assisted Reporting",           "adoption": "32%", "roi": "Medium", "complexity": "Low"},
    ],
    "stat": "Organisations that deploy AI in operations report average productivity gains of 20–30%.",
}


def get_industry_benchmarks(industry: str) -> dict:
    """Returns static benchmark data for the given industry."""
    return INDUSTRY_BENCHMARKS.get(industry, DEFAULT_BENCHMARK)


def enrich_with_gemini(industry: str, company: str, org_use_cases: list) -> dict:
    """
    Enriches static benchmarks with Gemini-generated insights.
    Connects org-specific use cases to industry trends.
    org_use_cases: list of use case titles from Phase 4
    """
    benchmarks = get_industry_benchmarks(industry)

    prompt = f"""You are presenting global AI adoption data in a workshop for {company} ({industry}).

Industry adoption rate: {benchmarks['adoption_rate']} of companies are using AI
Key stat: {benchmarks['stat']}
Top industry use cases: {', '.join([uc['title'] for uc in benchmarks['top_use_cases'][:3]])}
This organisation's proposed use cases: {', '.join(org_use_cases[:5]) if org_use_cases else 'Not yet generated'}

Return JSON:
{{
  "headline": "One striking sentence about AI adoption in this industry",
  "org_alignment": "One sentence: how well this org's priorities align with industry trends",
  "hidden_opportunity": "One use case the industry is adopting that this org hasn't mentioned yet",
  "urgency_signal": "One sentence: what happens to companies that delay AI adoption in this industry"
}}"""

    result = gemini_json(prompt)
    if result:
        return {**benchmarks, **result}

    return {
        **benchmarks,
        "headline": f"{benchmarks['adoption_rate']} of {industry} companies are actively using AI — the window for competitive advantage is narrowing.",
        "org_alignment": "Your priorities closely mirror what leading companies in this industry are implementing.",
        "hidden_opportunity": benchmarks["top_use_cases"][1]["title"] if len(benchmarks["top_use_cases"]) > 1 else "Intelligent Document Processing",
        "urgency_signal": "Companies that started AI pilots in 2023–24 are already reporting measurable ROI — waiting means catching up, not leading.",
    }


def cross_reference_org_use_cases(org_use_cases: list, industry: str) -> list:
    """
    Tags each org use case with its industry adoption rate if it matches a benchmark.
    Returns use cases with 'sector_validated' and 'industry_adoption' fields added.
    """
    benchmarks = get_industry_benchmarks(industry)
    benchmark_titles = {uc["title"].lower(): uc for uc in benchmarks["top_use_cases"]}

    enriched = []
    for uc in org_use_cases:
        match = None
        for bt, bdata in benchmark_titles.items():
            # Fuzzy keyword match
            uc_words = set(uc.get("title", "").lower().split())
            bm_words = set(bt.split())
            if len(uc_words & bm_words) >= 2:
                match = bdata
                break
        enriched.append({
            **uc,
            "sector_validated":   match is not None,
            "industry_adoption":  match["adoption"] if match else None,
            "industry_roi":       match["roi"] if match else None,
        })
    return enriched