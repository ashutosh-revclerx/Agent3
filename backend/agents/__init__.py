"""
agents/__init__.py
──────────────────
Exports all 7 workshop agents.
Import from here in main.py:
    from agents import facilitator, insight_mining, prompt_coaching, ...
"""
from agents import (
    facilitator,
    insight_mining,
    prompt_coaching,
    poll_consensus,
    industry_benchmark,
    prioritisation_roi,
    deck_builder,
)

__all__ = [
    "facilitator",
    "insight_mining",
    "prompt_coaching",
    "poll_consensus",
    "industry_benchmark",
    "prioritisation_roi",
    "deck_builder",
]