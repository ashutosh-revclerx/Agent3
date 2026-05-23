"""
backend/redis_client.py
───────────────────────
Redis connection + caching layer for the AI Consulting Copilot.

Provides async helpers for session, participant, and phase-data state that
replaces in-memory Python dicts so the backend is stateless across restarts.
Falls back gracefully when Redis is unreachable (logs a warning; in-memory
dict still works as a short-lived fallback).
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from env_loader import load_env

load_env()
logger = logging.getLogger("copilot.redis")

_redis: Optional[aioredis.Redis] = None

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def init_redis() -> None:
    """Open a Redis connection pool."""
    global _redis
    if _redis is not None:
        return

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        _redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=5,
        )
        await _redis.ping()
        logger.info("✅ Redis connected: %s", url)
    except Exception as exc:            # noqa: BLE001
        logger.warning("⚠️  Redis unavailable (%s) — falling back to in-memory only.", exc)
        _redis = None


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("✅ Redis connection closed")


def is_connected() -> bool:
    return _redis is not None


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

_DEFAULT_TTL = 24 * 60 * 60  # 24 hours


async def _set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    if _redis is None:
        return
    await _redis.set(key, json.dumps(value, default=str), ex=ttl)


async def _get(key: str) -> Optional[Any]:
    if _redis is None:
        return None
    raw = await _redis.get(key)
    return json.loads(raw) if raw else None


async def _delete(key: str) -> None:
    if _redis is None:
        return
    await _redis.delete(key)


async def _keys(pattern: str) -> List[str]:
    if _redis is None:
        return []
    return await _redis.keys(pattern)


# ---------------------------------------------------------------------------
# Session helpers  (key: session:<CODE>)
# ---------------------------------------------------------------------------

async def save_session(code: str, data: dict, ttl: int = _DEFAULT_TTL) -> None:
    await _set(f"session:{code.upper()}", data, ttl)


async def load_session(code: str) -> Optional[dict]:
    return await _get(f"session:{code.upper()}")


async def delete_session(code: str) -> None:
    await _delete(f"session:{code.upper()}")


async def load_all_sessions() -> Dict[str, dict]:
    """Return {code: session_dict} for every live session key in Redis."""
    keys = await _keys("session:*")
    result: Dict[str, dict] = {}
    for key in keys:
        data = await _get(key)
        if data:
            code = key.split(":", 1)[1]
            result[code] = data
    return result


# ---------------------------------------------------------------------------
# Participant helpers  (key: participant:<ID>)
# ---------------------------------------------------------------------------

async def save_participant(pid: str, data: dict, ttl: int = _DEFAULT_TTL) -> None:
    await _set(f"participant:{pid}", data, ttl)


async def load_participant(pid: str) -> Optional[dict]:
    return await _get(f"participant:{pid}")


async def delete_participant(pid: str) -> None:
    await _delete(f"participant:{pid}")


async def load_all_participants() -> Dict[str, dict]:
    """Return {participant_id: data} for every live participant in Redis."""
    keys = await _keys("participant:*")
    result: Dict[str, dict] = {}
    for key in keys:
        data = await _get(key)
        if data:
            pid = key.split(":", 1)[1]
            result[pid] = data
    return result


# ---------------------------------------------------------------------------
# Phase-data helpers  (key: phase_data:<CODE>:<PHASE_KEY>)
# ---------------------------------------------------------------------------

async def append_phase_entry(code: str, phase_key: str, entry: dict,
                              ttl: int = _DEFAULT_TTL) -> None:
    """Append *entry* to the list stored at phase_data:<CODE>:<PHASE_KEY>."""
    existing: list = await _get(f"phase_data:{code.upper()}:{phase_key}") or []
    existing.append(entry)
    await _set(f"phase_data:{code.upper()}:{phase_key}", existing, ttl)


async def load_phase_entries(code: str, phase_key: str) -> list:
    return await _get(f"phase_data:{code.upper()}:{phase_key}") or []


async def save_phase_entries(code: str, phase_key: str, entries: list,
                              ttl: int = _DEFAULT_TTL) -> None:
    await _set(f"phase_data:{code.upper()}:{phase_key}", entries, ttl)


async def load_all_phase_data(code: str) -> Dict[str, list]:
    """Return {phase_key: [entries]} for all phase keys belonging to *code*."""
    keys = await _keys(f"phase_data:{code.upper()}:*")
    result: Dict[str, list] = {}
    for key in keys:
        phase_key = key.split(":", 2)[2]
        result[phase_key] = await _get(key) or []
    return result
