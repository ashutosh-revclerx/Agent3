"""initial schema

Revision ID: 20260406_0001
Revises:
Create Date: 2026-04-06 03:10:00
"""
from __future__ import annotations

from alembic import op


revision = "20260406_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(6) UNIQUE NOT NULL,
            host_name VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            industry VARCHAR(100) NOT NULL,
            participant_count INT NOT NULL,
            duration_mins INT DEFAULT 90,
            current_phase INT DEFAULT 0,
            status VARCHAR(50) DEFAULT 'waiting',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revealed_phases TEXT[] DEFAULT ARRAY[]::TEXT[],
            workshop_data JSONB DEFAULT '{}'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS company_dna (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            company_name VARCHAR(255) NOT NULL,
            vision TEXT,
            goals TEXT[] DEFAULT ARRAY[]::TEXT[],
            products TEXT[] DEFAULT ARRAY[]::TEXT[],
            tone VARCHAR(100),
            recent_news TEXT[] DEFAULT ARRAY[]::TEXT[],
            confidence VARCHAR(20) CHECK (confidence IN ('complete', 'partial', 'fallback')),
            source_url VARCHAR(2048),
            scraped_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS participants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(100),
            company VARCHAR(255),
            headline VARCHAR(255),
            summary TEXT,
            skills TEXT[] DEFAULT ARRAY[]::TEXT[],
            location VARCHAR(255),
            industry VARCHAR(100),
            confidence VARCHAR(20) CHECK (confidence IN ('complete', 'partial', 'fallback')),
            source VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('linkedin', 'manual')),
            linkedin_url VARCHAR(2048),
            scraped_at TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS participant_extras (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            participant_id UUID UNIQUE REFERENCES participants(id) ON DELETE CASCADE,
            fun_fact TEXT,
            local_context JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS phase_data (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
            phase_key VARCHAR(100) NOT NULL,
            participant_id UUID REFERENCES participants(id) ON DELETE SET NULL,
            submission JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_sessions_code ON sessions(code)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_company_dna_session ON company_dna(session_id) WHERE is_active = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_company_dna_expires_at ON company_dna(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_company_dna_company_name ON company_dna(company_name)",
        "CREATE INDEX IF NOT EXISTS idx_participants_session ON participants(session_id) WHERE is_active = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_participants_name ON participants(name)",
        "CREATE INDEX IF NOT EXISTS idx_participants_expires_at ON participants(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_phase_data_session ON phase_data(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_phase_data_session_phase ON phase_data(session_id, phase_key)",
        "CREATE INDEX IF NOT EXISTS idx_phase_data_participant_id ON phase_data(participant_id)",
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_sessions_updated_at') THEN
                CREATE TRIGGER update_sessions_updated_at
                BEFORE UPDATE ON sessions
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_company_dna_updated_at') THEN
                CREATE TRIGGER update_company_dna_updated_at
                BEFORE UPDATE ON company_dna
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_participants_updated_at') THEN
                CREATE TRIGGER update_participants_updated_at
                BEFORE UPDATE ON participants
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_participant_extras_updated_at') THEN
                CREATE TRIGGER update_participant_extras_updated_at
                BEFORE UPDATE ON participant_extras
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_phase_data_updated_at') THEN
                CREATE TRIGGER update_phase_data_updated_at
                BEFORE UPDATE ON phase_data
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """,
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO copilot_user",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO copilot_user",
    ]

    bind = op.get_bind()
    for statement in statements:
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    statements = [
        "DROP TRIGGER IF EXISTS update_phase_data_updated_at ON phase_data",
        "DROP TRIGGER IF EXISTS update_participant_extras_updated_at ON participant_extras",
        "DROP TRIGGER IF EXISTS update_participants_updated_at ON participants",
        "DROP TRIGGER IF EXISTS update_company_dna_updated_at ON company_dna",
        "DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions",
        "DROP FUNCTION IF EXISTS update_updated_at_column()",
        "DROP TABLE IF EXISTS phase_data",
        "DROP TABLE IF EXISTS participant_extras",
        "DROP TABLE IF EXISTS participants",
        "DROP TABLE IF EXISTS company_dna",
        "DROP TABLE IF EXISTS sessions",
    ]

    bind = op.get_bind()
    for statement in statements:
        bind.exec_driver_sql(statement)
