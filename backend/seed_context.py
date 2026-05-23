"""
seed_context.py
───────────────
Pre-loaded business entity context injected into all agents
before any participant joins the workshop session.

Structure:
  THE BUSINESS ENTITY
  ├── Pillar 1: Sales & Marketing
  │   ├── Market Research
  │   ├── Advertising
  │   └── Sales Ops
  ├── Pillar 2: Operations & Fulfillment
  │   ├── Procurement
  │   ├── Production
  │   └── Logistics
  └── Pillar 3: Finance & Administration
      ├── Accounting
      ├── HR
      └── Legal

Usage:
  from seed_context import BUSINESS_CONTEXT, get_agent_seed
  context = get_agent_seed("insight_mining")
"""

# ─────────────────────────────────────────────────────────────────────────────
# MASTER BUSINESS ENTITY DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

BUSINESS_CONTEXT = {
    "entity": "The Business Entity",
    "pillars": [
        {
            "id": "sales_marketing",
            "name": "Sales & Marketing",
            "number": 1,
            "purpose": "Creating and closing demand",
            "departments": [
                {
                    "id": "market_research",
                    "name": "Market Research",
                    "function": "Understanding the need",
                    "core_activities": [
                        "Customer segmentation analysis",
                        "Competitor intelligence gathering",
                        "Market sizing and trend tracking",
                        "Voice-of-customer surveys and interviews",
                        "Win/loss analysis reporting",
                    ],
                    "typical_pain_points": [
                        "Manual data aggregation from multiple sources",
                        "Slow turnaround on competitor analysis",
                        "Inconsistent reporting formats across regions",
                        "Survey data sitting unanalysed in spreadsheets",
                        "No single source of truth for market data",
                    ],
                    "data_assets": [
                        "CRM customer records",
                        "Survey response databases",
                        "Web analytics and traffic data",
                        "Third-party market research reports",
                        "Social listening data",
                    ],
                    "ai_opportunities": [
                        "Automated competitor monitoring and alerting",
                        "AI-powered survey analysis and theme extraction",
                        "Predictive customer segmentation",
                        "Real-time market signal dashboards",
                        "Natural language win/loss report generation",
                    ],
                },
                {
                    "id": "advertising",
                    "name": "Advertising",
                    "function": "Creating the demand",
                    "core_activities": [
                        "Campaign planning and brief creation",
                        "Ad copy and creative development",
                        "Media buying and channel selection",
                        "Campaign performance monitoring",
                        "A/B testing and optimisation",
                    ],
                    "typical_pain_points": [
                        "Manual campaign performance reporting",
                        "Creative brief iterations taking too long",
                        "Ad copy review and approval bottlenecks",
                        "Budget allocation decisions based on stale data",
                        "Cross-channel attribution is unclear",
                    ],
                    "data_assets": [
                        "Ad platform performance data (Meta, Google, LinkedIn)",
                        "Campaign budget and spend records",
                        "Creative asset libraries",
                        "Audience targeting parameters",
                        "Historical campaign results",
                    ],
                    "ai_opportunities": [
                        "AI ad copy generation and variation testing",
                        "Automated campaign performance dashboards",
                        "Predictive budget allocation by channel",
                        "Audience lookalike modelling",
                        "Creative performance scoring before launch",
                    ],
                },
                {
                    "id": "sales_ops",
                    "name": "Sales Ops",
                    "function": "Closing the deal",
                    "core_activities": [
                        "Lead qualification and scoring",
                        "Pipeline management and forecasting",
                        "Proposal and quote generation",
                        "CRM data entry and hygiene",
                        "Sales performance reporting",
                    ],
                    "typical_pain_points": [
                        "Reps spending hours on manual CRM updates",
                        "Lead qualification is inconsistent across the team",
                        "Sales forecasts are based on gut feel not data",
                        "Proposal creation takes too long",
                        "No visibility into why deals are lost",
                    ],
                    "data_assets": [
                        "CRM pipeline data",
                        "Call recordings and transcripts",
                        "Email communication history",
                        "Proposal and contract documents",
                        "Pricing and discount history",
                    ],
                    "ai_opportunities": [
                        "AI lead scoring and qualification automation",
                        "Automated CRM data entry from calls/emails",
                        "AI-generated proposals from templates",
                        "Predictive sales forecasting",
                        "Deal risk scoring and early warning system",
                    ],
                },
            ],
        },
        {
            "id": "operations_fulfillment",
            "name": "Operations & Fulfillment",
            "number": 2,
            "purpose": "Creating and delivering value",
            "departments": [
                {
                    "id": "procurement",
                    "name": "Procurement",
                    "function": "Getting the materials",
                    "core_activities": [
                        "Supplier identification and vetting",
                        "Purchase order creation and approval",
                        "Supplier performance monitoring",
                        "Contract negotiation and management",
                        "Inventory demand planning",
                    ],
                    "typical_pain_points": [
                        "Manual purchase order creation from emails",
                        "Supplier performance data scattered across systems",
                        "Slow approval workflows for urgent purchases",
                        "No visibility into spend by category",
                        "Contract renewal dates missed",
                    ],
                    "data_assets": [
                        "Supplier database and performance records",
                        "Purchase order history",
                        "Inventory levels and movement data",
                        "Contract documents and renewal dates",
                        "Spend analytics by category",
                    ],
                    "ai_opportunities": [
                        "Automated purchase order generation",
                        "AI supplier risk scoring and monitoring",
                        "Demand forecasting for inventory planning",
                        "Contract expiry alerting and renewal drafts",
                        "Spend anomaly detection",
                    ],
                },
                {
                    "id": "production",
                    "name": "Production",
                    "function": "Creating the value",
                    "core_activities": [
                        "Production scheduling and capacity planning",
                        "Quality control and defect tracking",
                        "Equipment maintenance scheduling",
                        "Output and throughput reporting",
                        "Process documentation and SOPs",
                    ],
                    "typical_pain_points": [
                        "Production schedules built manually in spreadsheets",
                        "Quality defects discovered late in the process",
                        "Unplanned equipment downtime causes delays",
                        "SOPs out of date and hard to find",
                        "Output reporting takes hours to compile",
                    ],
                    "data_assets": [
                        "Production run logs and output data",
                        "Equipment performance and maintenance records",
                        "Quality control inspection results",
                        "Capacity and shift scheduling data",
                        "SOP and process documentation",
                    ],
                    "ai_opportunities": [
                        "AI production scheduling optimisation",
                        "Predictive quality control and defect detection",
                        "Predictive maintenance for equipment",
                        "Automated output reporting dashboards",
                        "AI-assisted SOP generation and version control",
                    ],
                },
                {
                    "id": "logistics",
                    "name": "Logistics",
                    "function": "Delivering the result",
                    "core_activities": [
                        "Order fulfilment and dispatch coordination",
                        "Carrier selection and rate negotiation",
                        "Shipment tracking and exception management",
                        "Returns processing",
                        "Delivery performance reporting",
                    ],
                    "typical_pain_points": [
                        "Manual order dispatch coordination across carriers",
                        "Shipment exceptions handled reactively",
                        "Customer enquiries about delivery status require manual lookup",
                        "Returns processing is slow and paper-based",
                        "Carrier performance not tracked systematically",
                    ],
                    "data_assets": [
                        "Order management system data",
                        "Carrier tracking and performance data",
                        "Delivery success and exception logs",
                        "Returns and refund records",
                        "Customer delivery satisfaction scores",
                    ],
                    "ai_opportunities": [
                        "AI carrier selection and rate optimisation",
                        "Proactive shipment exception alerting",
                        "AI customer delivery status chatbot",
                        "Automated returns processing and routing",
                        "Delivery performance prediction by route",
                    ],
                },
            ],
        },
        {
            "id": "finance_administration",
            "name": "Finance & Administration",
            "number": 3,
            "purpose": "Tracking money, people, and risk",
            "departments": [
                {
                    "id": "accounting",
                    "name": "Accounting",
                    "function": "Tracking the money",
                    "core_activities": [
                        "Accounts payable and receivable processing",
                        "Month-end close and reconciliation",
                        "Financial reporting and analysis",
                        "Invoice processing and matching",
                        "Expense management and approval",
                    ],
                    "typical_pain_points": [
                        "Invoice processing is manual and slow",
                        "Month-end close takes too long",
                        "Expense reports submitted late and incomplete",
                        "Reconciliation errors found after close",
                        "Financial reports compiled manually in Excel",
                    ],
                    "data_assets": [
                        "General ledger and chart of accounts",
                        "Accounts payable and receivable records",
                        "Invoice and purchase order data",
                        "Expense claim records",
                        "Bank statements and transaction history",
                    ],
                    "ai_opportunities": [
                        "AI invoice data extraction and matching",
                        "Automated month-end reconciliation",
                        "Expense anomaly detection and policy checking",
                        "AI financial narrative generation for reports",
                        "Cash flow forecasting with ML",
                    ],
                },
                {
                    "id": "hr",
                    "name": "HR",
                    "function": "Managing the people",
                    "core_activities": [
                        "Recruitment and candidate screening",
                        "Onboarding and offboarding",
                        "Performance review coordination",
                        "Payroll processing and queries",
                        "HR policy management and compliance",
                    ],
                    "typical_pain_points": [
                        "CV screening takes too much recruiter time",
                        "Onboarding is inconsistent across departments",
                        "Performance review data scattered across emails",
                        "Payroll queries handled manually",
                        "Policy documents out of date and hard to find",
                    ],
                    "data_assets": [
                        "Employee records and HRIS data",
                        "Recruitment pipeline and applicant data",
                        "Performance review history",
                        "Payroll and compensation records",
                        "Training completion records",
                    ],
                    "ai_opportunities": [
                        "AI CV screening and candidate shortlisting",
                        "Automated onboarding workflow and checklist",
                        "AI HR policy assistant and Q&A chatbot",
                        "Performance pattern analysis and early warning",
                        "Payroll anomaly detection",
                    ],
                },
                {
                    "id": "legal",
                    "name": "Legal",
                    "function": "Managing the risk",
                    "core_activities": [
                        "Contract drafting and review",
                        "Compliance monitoring and reporting",
                        "Risk assessment and documentation",
                        "Regulatory filing and tracking",
                        "Intellectual property management",
                    ],
                    "typical_pain_points": [
                        "Contract review is a bottleneck for deals",
                        "Compliance deadlines tracked manually in calendars",
                        "No centralised contract repository",
                        "Risk registers updated infrequently",
                        "Regulatory changes discovered late",
                    ],
                    "data_assets": [
                        "Contract repository (signed agreements)",
                        "Compliance checklists and audit trails",
                        "Risk register and issue log",
                        "Regulatory filing history",
                        "IP registration records",
                    ],
                    "ai_opportunities": [
                        "AI contract review and risk flagging",
                        "Automated compliance monitoring and alerting",
                        "Contract repository with AI search",
                        "Regulatory change monitoring and digest",
                        "Risk register auto-population from incidents",
                    ],
                },
            ],
        },
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS — used by agents to access context
# ─────────────────────────────────────────────────────────────────────────────

def get_all_departments() -> list:
    """Returns flat list of all 9 department dicts."""
    deps = []
    for pillar in BUSINESS_CONTEXT["pillars"]:
        for dept in pillar["departments"]:
            deps.append({**dept, "pillar": pillar["name"], "pillar_id": pillar["id"]})
    return deps


def get_department(dept_id: str) -> dict | None:
    """Returns a single department dict by id."""
    for dept in get_all_departments():
        if dept["id"] == dept_id:
            return dept
    return None


def get_pillar(pillar_id: str) -> dict | None:
    """Returns a pillar dict by id."""
    for p in BUSINESS_CONTEXT["pillars"]:
        if p["id"] == pillar_id:
            return p
    return None


def get_department_names() -> list[str]:
    """Returns all 9 department name strings."""
    return [d["name"] for d in get_all_departments()]


def get_all_pain_points() -> list[dict]:
    """
    Returns all known pain points with department and pillar tags.
    Used by Insight Mining Agent to pre-seed problem clustering.
    """
    out = []
    for dept in get_all_departments():
        for pain in dept["typical_pain_points"]:
            out.append({
                "text":       pain,
                "department": dept["name"],
                "pillar":     dept["pillar"],
                "dept_id":    dept["id"],
                "pillar_id":  dept["pillar_id"],
                "source":     "seed",
            })
    return out


def get_all_ai_opportunities() -> list[dict]:
    """
    Returns all AI opportunity suggestions across all departments.
    Used by Industry Benchmark Agent and Prioritisation Agent.
    """
    out = []
    for dept in get_all_departments():
        for opp in dept["ai_opportunities"]:
            out.append({
                "title":      opp,
                "department": dept["name"],
                "pillar":     dept["pillar"],
                "dept_id":    dept["id"],
                "source":     "seed",
            })
    return out


def get_all_data_assets() -> list[dict]:
    """
    Returns all data assets across departments.
    Used by Activity A Data Audit to pre-populate dataset suggestions.
    """
    out = []
    for dept in get_all_departments():
        for asset in dept["data_assets"]:
            out.append({
                "asset":      asset,
                "department": dept["name"],
                "pillar":     dept["pillar"],
                "dept_id":    dept["id"],
            })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# AGENT SEED PAYLOADS
# Each agent gets a tailored context dict injected at session creation
# ─────────────────────────────────────────────────────────────────────────────

def get_agent_seed(agent_name: str) -> dict:
    """
    Returns the relevant seed context for a specific agent.

    Usage in main.py:
        from seed_context import get_agent_seed
        session["seed"] = {
            agent: get_agent_seed(agent)
            for agent in ["facilitator","insight_mining","prompt_coaching",
                          "poll_consensus","industry_benchmark",
                          "prioritisation_roi","deck_builder"]
        }
    """
    seeds = {

        # ── Agent 1: Facilitator ──────────────────────────────────────────────
        "facilitator": {
            "description": "Uses pillar structure to personalise phase introductions per department",
            "pillars": [p["name"] for p in BUSINESS_CONTEXT["pillars"]],
            "departments": get_department_names(),
            "pillar_purposes": {
                p["name"]: p["purpose"]
                for p in BUSINESS_CONTEXT["pillars"]
            },
            "intro_hint": (
                "This organisation operates across 3 pillars: Sales & Marketing, "
                "Operations & Fulfillment, and Finance & Administration. "
                "Tailor phase introductions to reference these areas naturally."
            ),
        },

        # ── Agent 2: Insight Mining ───────────────────────────────────────────
        "insight_mining": {
            "description": "Pre-seeds problem clusters and objective themes from known pain points",
            "known_pain_points": get_all_pain_points(),
            "department_structure": {
                pillar["name"]: [d["name"] for d in pillar["departments"]]
                for pillar in BUSINESS_CONTEXT["pillars"]
            },
            "expected_cluster_themes": [
                "Manual data entry and process automation",
                "Reporting and visibility gaps",
                "Cross-system data silos",
                "Approval workflow bottlenecks",
                "Compliance and risk tracking",
            ],
            "clustering_hint": (
                "When clustering problems, map them to one of the 9 departments. "
                "Flag cross-pillar patterns (e.g. manual reporting appearing in both "
                "Sales Ops and Accounting) as high-priority sector-validated signals."
            ),
        },

        # ── Agent 3: Prompt Coaching ──────────────────────────────────────────
        "prompt_coaching": {
            "description": "Uses department context to make prompt simulations realistic",
            "department_examples": {
                dept["name"]: dept["core_activities"][0]
                for dept in get_all_departments()
            },
            "simulation_hint": (
                "When running a live simulation, ground the AI response in the "
                "participant's department context. Use realistic but fictional data "
                "that matches what that department actually works with."
            ),
        },

        # ── Agent 4: Poll & Consensus ─────────────────────────────────────────
        "poll_consensus": {
            "description": "Weights votes by pillar to detect cross-functional consensus",
            "pillars": [p["name"] for p in BUSINESS_CONTEXT["pillars"]],
            "departments": get_department_names(),
            "consensus_hint": (
                "A use case that gets votes from participants across all 3 pillars "
                "is stronger than one that only attracts votes from a single pillar. "
                "Flag cross-pillar consensus separately — it signals org-wide impact."
            ),
        },

        # ── Agent 5: Industry Benchmark ───────────────────────────────────────
        "industry_benchmark": {
            "description": "Maps industry AI adoption data to each pillar's known opportunities",
            "seeded_opportunities": get_all_ai_opportunities(),
            "pillar_adoption_context": {
                "Sales & Marketing": (
                    "AI adoption is highest here — lead scoring, content generation, "
                    "and CRM automation are deployed by 60%+ of mid-market companies."
                ),
                "Operations & Fulfillment": (
                    "Predictive maintenance and demand forecasting are proven high-ROI "
                    "use cases. Supply chain AI adoption growing at 35% YoY."
                ),
                "Finance & Administration": (
                    "Invoice processing and contract review AI are now mainstream. "
                    "Finance teams using AI report 30–40% reduction in manual processing time."
                ),
            },
            "benchmark_hint": (
                "During Phase 6, present adoption data per pillar. "
                "Show that some opportunities the team voted for are already "
                "industry-standard — this validates their instincts and builds confidence."
            ),
        },

        # ── Agent 6: Prioritisation & ROI ─────────────────────────────────────
        "prioritisation_roi": {
            "description": "Uses known data assets to assess readiness per use case",
            "data_assets_by_dept": {
                dept["name"]: dept["data_assets"]
                for dept in get_all_departments()
            },
            "quick_win_candidates": [
                "AI lead scoring and qualification automation",
                "Automated CRM data entry from calls/emails",
                "AI invoice data extraction and matching",
                "AI CV screening and candidate shortlisting",
                "Automated campaign performance dashboards",
            ],
            "scoring_hint": (
                "Departments with structured, centralised data (Accounting, Sales Ops) "
                "have higher data readiness. Departments with scattered data "
                "(Market Research, Legal) need data preparation before AI deployment."
            ),
        },

        # ── Agent 7: Deck Builder ─────────────────────────────────────────────
        "deck_builder": {
            "description": "Structures deliverables around the 3-pillar framework",
            "slide_structure_hint": (
                "Organise the use case slide by pillar — one section per pillar. "
                "Show which pillar has the most quick wins vs which needs longer-term investment."
            ),
            "roadmap_hint": (
                "Phase 1 quick wins should come from Sales Ops and Accounting — "
                "they have the cleanest data and highest volume of repetitive tasks. "
                "Operations AI (predictive maintenance, demand forecasting) typically "
                "lands in Phase 2 due to data preparation requirements."
            ),
            "pillar_summaries": {
                pillar["name"]: {
                    "purpose": pillar["purpose"],
                    "departments": [d["name"] for d in pillar["departments"]],
                    "ai_count": sum(len(d["ai_opportunities"]) for d in pillar["departments"]),
                }
                for pillar in BUSINESS_CONTEXT["pillars"]
            },
        },
    }

    return seeds.get(agent_name, {})


# ─────────────────────────────────────────────────────────────────────────────
# SESSION SEEDING — call this when creating a new session
# ─────────────────────────────────────────────────────────────────────────────

AGENT_NAMES = [
    "facilitator",
    "insight_mining",
    "prompt_coaching",
    "poll_consensus",
    "industry_benchmark",
    "prioritisation_roi",
    "deck_builder",
]

def seed_session(session: dict) -> dict:
    """
    Injects seed context into a session dict at creation time.
    Call this in main.py create_session() after the session dict is built.

    Returns the session dict with seed data attached.

    Example:
        session = { "id": ..., "code": ..., "company": ... }
        session = seed_session(session)
        sessions[code] = session
    """
    session["seed"] = {
        agent: get_agent_seed(agent)
        for agent in AGENT_NAMES
    }
    session["department_map"] = {
        pillar["name"]: [d["name"] for d in pillar["departments"]]
        for pillar in BUSINESS_CONTEXT["pillars"]
    }
    session["known_departments"] = get_department_names()
    session["pillar_names"] = [p["name"] for p in BUSINESS_CONTEXT["pillars"]]
    return session


def build_system_prompt(agent_name: str, session: dict) -> str:
    """
    Builds a Gemini system prompt string for a given agent,
    incorporating both the seed context and live session data.

    Usage in agents:
        from seed_context import build_system_prompt
        system = build_system_prompt("insight_mining", session)
        gemini_text(prompt, system=system)
    """
    seed  = session.get("seed", {}).get(agent_name, {})
    company   = session.get("company", "the organisation")
    industry  = session.get("industry", "")
    hint      = seed.get(f"{agent_name}_hint") or seed.get("clustering_hint") or \
                seed.get("consensus_hint") or seed.get("simulation_hint") or \
                seed.get("intro_hint") or seed.get("scoring_hint") or \
                seed.get("roadmap_hint") or ""

    dept_list = ", ".join(session.get("known_departments", get_department_names()))
    pillar_list = ", ".join(session.get("pillar_names", [p["name"] for p in BUSINESS_CONTEXT["pillars"]]))

    return (
        f"You are an AI strategy consultant working with {company}"
        f"{' in the ' + industry + ' sector' if industry else ''}.\n\n"
        f"This organisation operates across 3 business pillars: {pillar_list}.\n"
        f"The 9 departments are: {dept_list}.\n\n"
        f"{hint}\n\n"
        f"Always ground your analysis in this organisational context. "
        f"Be specific, practical, and reference the relevant departments by name."
    )