"""
agents/__init__.py
──────────────────
Exports all agents and utility modules.
Import from here in main.py:
    from agents import facilitator, insight_mining, prompt_coaching, ...
"""
from . import (
    facilitator,
    insight_mining,
    prompt_coaching,
    poll_consensus,
    industry_benchmark,
    prioritisation_roi,
    deck_builder,
    scraping_agent,
    opportunity_generation,
)

__all__ = [
    "facilitator",
    "insight_mining",
    "prompt_coaching",
    "poll_consensus",
    "industry_benchmark",
    "prioritisation_roi",
    "deck_builder",
    "scraping_agent",
    "opportunity_generation",
]