"""
agents/poll_consensus.py
────────────────────────
POLL AND CONSENSUS AGENT
────────────────────────
Responsibility:
  - Manages live voting in Phase 5 (initial poll) and Phase 7 (second poll)
  - Aggregates and ranks participant votes
  - Detects consensus — when strong agreement emerges
  - Measures vote shift between Poll 1 and Poll 2
  - A use case that GAINS votes after education (Phase 6) carries more strategic weight

Activated: Phase 5 (initial poll) and Phase 7 (second poll)
"""
from gemini_client import gemini_json
from typing import List


def tally_votes(votes: list, use_cases: list) -> list:
    """
    Tallies votes for each use case and returns ranked results.

    votes:     list of { participant_id, voted_ids: [use_case_id, ...] }
    use_cases: list of { id, title, ... }

    Returns: sorted list of { id, title, vote_count, vote_pct, rank }
    """
    counts = {}
    total_voters = len(votes)

    for vote in votes:
        for uid in vote.get("voted_ids", []):
            counts[uid] = counts.get(uid, 0) + 1

    results = []
    for uc in use_cases:
        uid   = uc.get("id")
        count = counts.get(uid, 0)
        results.append({
            **uc,
            "vote_count": count,
            "vote_pct":   round((count / max(total_voters, 1)) * 100),
        })

    results.sort(key=lambda x: x["vote_count"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results


def detect_consensus(poll_results: list, threshold: float = 0.6) -> dict:
    """
    Detects whether strong consensus exists.
    threshold: fraction of voters needed to flag as consensus (default 60%)

    Returns: { has_consensus, consensus_items, consensus_strength }
    """
    if not poll_results:
        return {"has_consensus": False, "consensus_items": [], "consensus_strength": 0}

    top_vote_pct = poll_results[0].get("vote_pct", 0) / 100
    consensus_items = [r for r in poll_results if (r.get("vote_pct", 0) / 100) >= threshold]

    return {
        "has_consensus":      len(consensus_items) > 0,
        "consensus_items":    [r.get("title") for r in consensus_items],
        "consensus_strength": round(top_vote_pct * 100),
    }


def measure_vote_shift(poll1_results: list, poll2_results: list) -> list:
    """
    Compares Poll 1 vs Poll 2 results.
    Use cases that GAIN votes after the benchmark education (Phase 6)
    are flagged as 'education-validated' — they carry more strategic weight.

    Returns: list of { id, title, poll1_rank, poll2_rank, shift, education_validated }
    """
    poll1_map = {r["id"]: r for r in poll1_results}
    poll2_map = {r["id"]: r for r in poll2_results}

    all_ids = set(list(poll1_map.keys()) + list(poll2_map.keys()))
    shifts  = []

    for uid in all_ids:
        p1 = poll1_map.get(uid, {})
        p2 = poll2_map.get(uid, {})
        p1_votes = p1.get("vote_count", 0)
        p2_votes = p2.get("vote_count", 0)
        shift    = p2_votes - p1_votes
        shifts.append({
            "id":                  uid,
            "title":               p2.get("title") or p1.get("title", "Unknown"),
            "poll1_votes":         p1_votes,
            "poll2_votes":         p2_votes,
            "shift":               shift,
            "education_validated": shift > 0,  # gained votes after seeing global data
        })

    shifts.sort(key=lambda x: x["poll2_votes"], reverse=True)
    return shifts


def generate_consensus_insight(company: str, poll_results: list,
                                shift_data: list = None) -> str:
    """
    Uses Gemini to generate a 2-sentence insight about voting patterns.
    """
    top = poll_results[:3] if poll_results else []
    top_names = [r.get("title", "") for r in top]
    validated = [s["title"] for s in (shift_data or []) if s.get("education_validated")]

    prompt = (
        f"Workshop insight for {company}.\n"
        f"Top voted AI use cases: {', '.join(top_names)}\n"
        f"{'Use cases that gained votes after education: ' + ', '.join(validated) if validated else ''}\n\n"
        "Write 2 sentences: what the voting pattern tells us about this organisation's AI priorities. "
        "Be specific and strategic. No bullet points."
    )

    result = gemini_json(prompt)
    if isinstance(result, str):
        return result

    # Fallback
    if validated:
        return (
            f"The team's strongest consensus is around {top_names[0] if top_names else 'automation'}. "
            f"Notably, {validated[0]} gained support after seeing global adoption data — "
            f"a strong signal it should be prioritised."
        )
    return (
        f"{company}'s team aligned most strongly around {top_names[0] if top_names else 'AI automation'}. "
        f"This reflects the operational priorities surfaced earlier in the workshop."
    )