"""
backend/db.py
─────────────
Database connection and query layer for PostgreSQL.
Handles all CRUD operations for sessions, company_dna, participants, and phase_data.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import uuid

import asyncpg
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger("copilot.db")

# Database connection pool (singleton)
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
        logger.info(f"Database pool initialized: {db_host}:{db_port}/{db_name}")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
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

# ─────────────────────────────────────────────────────────────────────────────
# Session Operations
# ─────────────────────────────────────────────────────────────────────────────

async def create_session(
    code: str,
    host_name: str,
    company: str,
    industry: str,
    participant_count: int,
    duration_mins: int = 90,
) -> Dict[str, Any]:
    """Create a new session in the database."""
    session_id = str(uuid.uuid4())
    
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO sessions 
            (id, code, host_name, company, industry, participant_count, duration_mins, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'waiting')
            """,
            session_id, code, host_name, company, industry, participant_count, duration_mins
        )
        logger.info(f"Session created: {code} ({session_id})")
    
    return {"id": session_id, "code": code}

async def get_session(code: str) -> Optional[Dict[str, Any]]:
    """Retrieve session by code."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE code = $1",
            code.upper()
        )
        if row:
            return dict(row)
    return None

async def update_session_phase(code: str, phase: int) -> None:
    """Update session current phase."""
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE sessions SET current_phase = $1 WHERE code = $2",
            phase, code.upper()
        )
        logger.debug(f"Session {code} updated to phase {phase}")

async def add_revealed_phase(code: str, phase: str) -> None:
    """Add a revealed phase to session."""
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE sessions 
            SET revealed_phases = array_append(revealed_phases, $1)
            WHERE code = $2 AND NOT $1 = ANY(revealed_phases)
            """,
            phase, code.upper()
        )

async def update_session_workshop_data(code: str, key: str, value: Any) -> None:
    """Update workshop_data JSONB field."""
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE sessions 
            SET workshop_data = jsonb_set(workshop_data, $1, $2)
            WHERE code = $3
            """,
            [key], value, code.upper()
        )

# ─────────────────────────────────────────────────────────────────────────────
# Company DNA Operations
# ─────────────────────────────────────────────────────────────────────────────

async def store_company_dna(
    session_code: str,
    dna_data: Dict[str, Any],
) -> Optional[str]:
    """Store company DNA in database with 30-day TTL."""
    dna_id = str(uuid.uuid4())
    scraped_at = datetime.fromisoformat(dna_data["scraped_at"]) if isinstance(dna_data["scraped_at"], str) else dna_data["scraped_at"]
    expires_at = scraped_at + timedelta(days=30)
    
    async with get_connection() as conn:
        # Get session ID
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper()
        )
        
        if not session:
            logger.error(f"Session {session_code} not found for company_dna storage")
            return None
        
        try:
            await conn.execute(
                """
                INSERT INTO company_dna 
                (id, session_id, company_name, vision, goals, products, tone, recent_news, 
                 confidence, source_url, scraped_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                dna_id,
                session["id"],
                dna_data.get("company_name", ""),
                dna_data.get("vision", ""),
                dna_data.get("goals", []),
                dna_data.get("products", []),
                dna_data.get("tone", ""),
                dna_data.get("recent_news", []),
                dna_data.get("confidence", "fallback"),
                dna_data.get("source_url", ""),
                scraped_at,
                expires_at
            )
            logger.info(f"Company DNA stored: {dna_id} for {session_code}")
            return dna_id
        except Exception as e:
            logger.error(f"Failed to store company DNA: {e}")
            return None

async def get_company_dna(session_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve active (non-expired) company DNA for a session."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT cd.* FROM company_dna cd
            JOIN sessions s ON cd.session_id = s.id
            WHERE s.code = $1 AND cd.is_active = TRUE AND cd.expires_at > NOW()
            ORDER BY cd.created_at DESC
            LIMIT 1
            """,
            session_code.upper()
        )
        if row:
            return dict(row)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Participant Operations
# ─────────────────────────────────────────────────────────────────────────────

async def create_participant(
    session_code: str,
    profile_data: Dict[str, Any],
) -> Optional[str]:
    """Create participant record with confirmed data."""
    participant_id = str(uuid.uuid4())
    
    scraped_at = None
    expires_at = None
    if profile_data.get("scraped_at"):
        if isinstance(profile_data["scraped_at"], str):
            scraped_at = datetime.fromisoformat(profile_data["scraped_at"])
        else:
            scraped_at = profile_data["scraped_at"]
        expires_at = scraped_at + timedelta(days=7)
    
    async with get_connection() as conn:
        # Get session ID
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper()
        )
        
        if not session:
            logger.error(f"Session {session_code} not found for participant creation")
            return None
        
        try:
            await conn.execute(
                """
                INSERT INTO participants 
                (id, session_id, name, role, company, headline, summary, skills, 
                 location, industry, confidence, source, linkedin_url, scraped_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """,
                participant_id,
                session["id"],
                profile_data.get("name", ""),
                profile_data.get("role", ""),
                profile_data.get("company", ""),
                profile_data.get("headline", ""),
                profile_data.get("summary", ""),
                profile_data.get("skills", []),
                profile_data.get("location", ""),
                profile_data.get("industry", ""),
                profile_data.get("confidence", "fallback"),
                profile_data.get("source", "manual"),
                profile_data.get("linkedin_url", ""),
                scraped_at,
                expires_at
            )
            
            # Store fun_fact and local_context separately
            if profile_data.get("fun_fact") or profile_data.get("local_context"):
                await conn.execute(
                    """
                    INSERT INTO participant_extras 
                    (participant_id, fun_fact, local_context)
                    VALUES ($1, $2, $3)
                    """,
                    participant_id,
                    profile_data.get("fun_fact"),
                    profile_data.get("local_context") or {}
                )
            
            logger.info(f"Participant created: {participant_id} for {session_code}")
            return participant_id
        except Exception as e:
            logger.error(f"Failed to create participant: {e}")
            return None

async def get_participants(session_code: str) -> List[Dict[str, Any]]:
    """Retrieve all active participants for a session."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT p.*, pe.fun_fact, pe.local_context
            FROM participants p
            LEFT JOIN participant_extras pe ON p.id = pe.participant_id
            WHERE p.session_id = (SELECT id FROM sessions WHERE code = $1)
            AND p.is_active = TRUE
            AND (p.expires_at IS NULL OR p.expires_at > NOW())
            ORDER BY p.created_at ASC
            """,
            session_code.upper()
        )
        return [dict(row) for row in rows]

async def get_participant(participant_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific participant."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT p.*, pe.fun_fact, pe.local_context
            FROM participants p
            LEFT JOIN participant_extras pe ON p.id = pe.participant_id
            WHERE p.id = $1
            """,
            uuid.UUID(participant_id)
        )
        if row:
            return dict(row)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Phase Data Operations
# ─────────────────────────────────────────────────────────────────────────────

async def store_phase_submission(
    session_code: str,
    phase_key: str,
    submission: Dict[str, Any],
    participant_id: Optional[str] = None,
) -> Optional[str]:
    """Store a phase submission."""
    submission_id = str(uuid.uuid4())
    
    async with get_connection() as conn:
        session = await conn.fetchrow(
            "SELECT id FROM sessions WHERE code = $1",
            session_code.upper()
        )
        
        if not session:
            logger.error(f"Session {session_code} not found")
            return None
        
        try:
            await conn.execute(
                """
                INSERT INTO phase_data 
                (id, session_id, phase_key, participant_id, submission)
                VALUES ($1, $2, $3, $4, $5)
                """,
                submission_id,
                session["id"],
                phase_key,
                uuid.UUID(participant_id) if participant_id else None,
                submission
            )
            logger.info(f"Phase submission stored: {phase_key} for {session_code}")
            return submission_id
        except Exception as e:
            logger.error(f"Failed to store phase submission: {e}")
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
            phase_key
        )
        return [dict(row) for row in rows]
