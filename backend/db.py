"""
backend/db.py
Database connection and query layer for PostgreSQL.
Handles CRUD operations for sessions, company_dna, participants, and phase_data.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg

from env_loader import load_env

load_env()

logger = logging.getLogger("copilot.db")

_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool."""
    global _pool
    if _pool is not None:
        return

    db_user = os.getenv("DB_USER", "copilot_user")
    db_password = os.getenv("DB_PASSWORD", "copilot_password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "copilot_db")

    try:
        _pool = await asyncpg.create_pool(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        logger.info("Database pool initialized: %s:%s/%s", db_host, db_port, db_name)
    except Exception as exc:
        logger.error("Failed to initialize database pool: %s", exc)
        raise


async def close_db():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


@asynccontextmanager
async def get_connection():
    """Get a connection from the pool."""
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")

    async with _pool.acquire() as conn:
        yield conn


async def create_session(
    code: str,
    host_name: str,
    company: str,
    industry: str,
    participant_count: int = 0,
    duration_mins: int = 90,
    avatar_id: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new session in the database."""
    session_id = str(uuid.uuid4())

    async with get_connection() as conn:
        try:
            await conn.execute(
                """
                INSERT INTO sessions (
                    id, code, host_name, company, industry,
                    participant_count, duration_mins, current_phase, status,
                    avatar_id, voice_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, 0, 'waiting', $8, $9)
                """,
                session_id,
                code,
                host_name,
                company,
                industry,
                participant_count,
                duration_mins,
                avatar_id,
                voice_id,
            )
        except asyncpg.UndefinedColumnError:
            # Backward compatibility for lean schema where these columns were removed.
            await conn.execute(
                """
                INSERT INTO sessions (
                    id, code, host_name, company, industry, current_phase, status, avatar_id, voice_id
                )
                VALUES ($1, $2, $3, $4, $5, 0, 'waiting', $6, $7)
                """,
                session_id,
                code,
                host_name,
                company,
                industry,
                avatar_id,
                voice_id,
            )
        logger.info("Session created: %s (%s) | avatar=%s voice=%s", code, session_id, avatar_id, voice_id)

    return {"id": session_id, "code": code}


async def get_session(code: str) -> Optional[Dict[str, Any]]:
    """Retrieve session by code."""
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM sessions WHERE code = $1", code.upper())
        return dict(row) if row else None


async def update_session_phase(code: str, phase: int) -> None:
    """Update session current phase."""
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE sessions SET current_phase = $1 WHERE code = $2",
            phase,
            code.upper(),
        )
        logger.debug("Session %s updated to phase %s", code, phase)


async def store_company_dna(session_code: str, dna_data: Dict[str, Any]) -> Optional[str]:
    """Store company DNA in database."""
    dna_id = str(uuid.uuid4())
    scraped_at = dna_data.get("scraped_at")
    if isinstance(scraped_at, str):
        scraped_at = datetime.fromisoformat(scraped_at)

    async with get_connection() as conn:
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper(),
        )
        if not session:
            logger.error("Session %s not found for company_dna storage", session_code)
            return None

        try:
            await conn.execute(
                """
                INSERT INTO company_dna (
                    id, session_id, company_name, vision, goals, products, recent_news,
                    confidence, source_url, scraped_at, raw_markdown
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                dna_id,
                session["id"],
                dna_data.get("company_name", ""),
                dna_data.get("vision", ""),
                dna_data.get("goals", []),
                dna_data.get("products", []),
                dna_data.get("recent_news", []),
                dna_data.get("confidence", "fallback"),
                dna_data.get("source_url", ""),
                scraped_at,
                dna_data.get("raw_markdown"),
            )
            logger.info("Company DNA stored: %s for %s", dna_id, session_code)
            return dna_id
        except Exception as exc:
            logger.error("Failed to store company DNA: %s", exc)
            return None


async def get_company_dna(session_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve active company DNA for a session."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT cd.* FROM company_dna cd
            JOIN sessions s ON cd.session_id = s.id
            WHERE s.code = $1 AND cd.is_active = TRUE
            ORDER BY cd.created_at DESC
            LIMIT 1
            """,
            session_code.upper(),
        )
        return dict(row) if row else None


async def create_participant(session_code: str, profile_data: Dict[str, Any]) -> Optional[str]:
    """Create participant record with confirmed data."""
    participant_id = str(uuid.uuid4())
    scraped_at = profile_data.get("scraped_at")
    if isinstance(scraped_at, str):
        scraped_at = datetime.fromisoformat(scraped_at)

    async with get_connection() as conn:
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper(),
        )
        if not session:
            logger.error("Session %s not found for participant creation", session_code)
            return None

        try:
            await conn.execute(
                """
                INSERT INTO participants (
                    id, session_id, name, role, headline, skills, location,
                    confidence, source, linkedin_url, scraped_at, fun_fact, local_context
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                participant_id,
                session["id"],
                profile_data.get("name", ""),
                profile_data.get("role", ""),
                profile_data.get("headline", ""),
                profile_data.get("skills", []),
                profile_data.get("location", ""),
                profile_data.get("confidence", "fallback"),
                profile_data.get("source", "manual"),
                profile_data.get("linkedin_url", ""),
                scraped_at,
                profile_data.get("fun_fact"),
                profile_data.get("local_context") or {},
            )
            logger.info("Participant created: %s for %s", participant_id, session_code)
            return participant_id
        except Exception as exc:
            logger.error("Failed to create participant: %s", exc)
            return None


async def get_participants(session_code: str) -> List[Dict[str, Any]]:
    """Retrieve all active participants for a session."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT p.*
            FROM participants p
            WHERE p.session_id = (SELECT id FROM sessions WHERE code = $1)
            AND p.is_active = TRUE
            ORDER BY p.created_at ASC
            """,
            session_code.upper(),
        )
        return [dict(row) for row in rows]


async def get_participant(participant_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific participant."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM participants WHERE id = $1",
            uuid.UUID(participant_id),
        )
        return dict(row) if row else None


async def store_phase_submission(
    session_code: str,
    phase_key: str,
    submission: Dict[str, Any],
    participant_id: Optional[str] = None,
) -> Optional[str]:
    """Store a phase submission in the lean typed/raw schema."""
    submission_id = str(uuid.uuid4())

    async with get_connection() as conn:
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper(),
        )
        if not session:
            logger.error("Session %s not found", session_code)
            return None

        ai_maturity = submission.get("ai_maturity")
        if ai_maturity is None and isinstance(submission.get("ai_confidence"), int):
            ai_maturity = submission.get("ai_confidence")

        try:
            await conn.execute(
                """
                INSERT INTO phase_data (
                    id, session_id, phase_key, participant_id, ai_maturity,
                    company_ai_maturity, it_tools, pain_points, goals_short,
                    goals_long, top_concern, raw_response
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                submission_id,
                session["id"],
                phase_key,
                uuid.UUID(participant_id) if participant_id else None,
                ai_maturity,
                submission.get("company_ai_maturity"),
                submission.get("it_tools") or [],
                submission.get("pain_points") or [],
                submission.get("goals_short"),
                submission.get("goals_long"),
                submission.get("top_concern") or submission.get("top_challenge"),
                submission,
            )
            logger.info("Phase submission stored: %s for %s", phase_key, session_code)
            return submission_id
        except Exception as exc:
            logger.error("Failed to store phase submission: %s", exc)
            return None


async def get_phase_submissions(session_code: str, phase_key: str) -> List[Dict[str, Any]]:
    """Retrieve all submissions for a phase in a session."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM phase_data
            WHERE session_id = (SELECT id FROM sessions WHERE code = $1)
            AND phase_key = $2
            ORDER BY created_at ASC
            """,
            session_code.upper(),
            phase_key,
        )
        return [dict(row) for row in rows]
