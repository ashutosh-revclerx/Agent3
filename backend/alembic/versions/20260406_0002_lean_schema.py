"""lean schema

Revision ID: 20260406_0002
Revises: 20260406_0001
Create Date: 2026-04-06

Consolidates tables, types phase_data columns, and removes unused fields.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT, UUID


revision = "20260406_0002"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("sessions", "duration_mins")
    op.drop_column("sessions", "participant_count")
    op.drop_column("sessions", "workshop_data")
    op.drop_column("sessions", "revealed_phases")

    op.add_column(
        "company_dna",
        sa.Column(
            "raw_markdown",
            sa.Text(),
            nullable=True,
            comment="Raw markdown returned by Nexus API for re-extraction",
        ),
    )
    op.drop_column("company_dna", "expires_at")
    op.drop_column("company_dna", "tone")

    op.add_column(
        "participants",
        sa.Column(
            "fun_fact",
            sa.Text(),
            nullable=True,
            comment="Generated from confirmed participant data",
        ),
    )
    op.add_column(
        "participants",
        sa.Column(
            "local_context",
            JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="Regional weather and sports context",
        ),
    )

    op.execute(
        """
        UPDATE participants p
        SET
            fun_fact = pe.fun_fact,
            local_context = COALESCE(pe.local_context, '{}'::jsonb)
        FROM participant_extras pe
        WHERE pe.participant_id = p.id
        """
    )

    op.drop_table("participant_extras")

    op.drop_column("participants", "summary")
    op.drop_column("participants", "company")
    op.drop_column("participants", "industry")
    op.drop_column("participants", "expires_at")

    op.add_column(
        "phase_data",
        sa.Column(
            "ai_maturity",
            sa.SmallInteger(),
            nullable=True,
            comment="Participant AI confidence score from 1 to 5",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "company_ai_maturity",
            sa.String(length=50),
            nullable=True,
            comment="exploring | piloting | implementing | scaling",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "it_tools",
            ARRAY(TEXT()),
            nullable=True,
            server_default=sa.text("'{}'::text[]"),
            comment="Current tools and systems used by participant",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "pain_points",
            ARRAY(TEXT()),
            nullable=True,
            server_default=sa.text("'{}'::text[]"),
            comment="Pain points extracted from survey conversation",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "goals_short",
            sa.Text(),
            nullable=True,
            comment="Short-term goal from survey",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "goals_long",
            sa.Text(),
            nullable=True,
            comment="Long-term goal from survey",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "top_concern",
            sa.Text(),
            nullable=True,
            comment="Primary concern raised by participant",
        ),
    )
    op.add_column(
        "phase_data",
        sa.Column(
            "raw_response",
            JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="Full verbatim agent or participant exchange",
        ),
    )

    op.create_check_constraint(
        "ck_phase_data_ai_maturity_range",
        "phase_data",
        "ai_maturity BETWEEN 1 AND 5",
    )

    op.execute(
        """
        UPDATE phase_data
        SET raw_response = submission
        WHERE submission IS NOT NULL
          AND submission != '{}'::jsonb
        """
    )

    op.drop_column("phase_data", "submission")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_phase_data_session_id ON phase_data (session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_phase_data_participant_phase ON phase_data (participant_id, phase_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_participants_session_active ON participants (session_id, is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_company_dna_session_active ON company_dna (session_id, is_active)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_phase_data_session_id")
    op.execute("DROP INDEX IF EXISTS ix_phase_data_participant_phase")
    op.execute("DROP INDEX IF EXISTS ix_participants_session_active")
    op.execute("DROP INDEX IF EXISTS ix_company_dna_session_active")

    op.add_column(
        "phase_data",
        sa.Column(
            "submission",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.execute(
        """
        UPDATE phase_data
        SET submission = raw_response
        WHERE raw_response IS NOT NULL
          AND raw_response != '{}'::jsonb
        """
    )

    op.drop_constraint("ck_phase_data_ai_maturity_range", "phase_data", type_="check")
    op.drop_column("phase_data", "raw_response")
    op.drop_column("phase_data", "top_concern")
    op.drop_column("phase_data", "goals_long")
    op.drop_column("phase_data", "goals_short")
    op.drop_column("phase_data", "pain_points")
    op.drop_column("phase_data", "it_tools")
    op.drop_column("phase_data", "company_ai_maturity")
    op.drop_column("phase_data", "ai_maturity")

    op.create_table(
        "participant_extras",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "participant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("participants.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("fun_fact", sa.Text(), nullable=True),
        sa.Column(
            "local_context",
            JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.execute(
        """
        INSERT INTO participant_extras (participant_id, fun_fact, local_context)
        SELECT id, fun_fact, COALESCE(local_context, '{}'::jsonb)
        FROM participants
        WHERE fun_fact IS NOT NULL
           OR (local_context IS NOT NULL AND local_context != '{}'::jsonb)
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_participant_extras_updated_at') THEN
                CREATE TRIGGER update_participant_extras_updated_at
                BEFORE UPDATE ON participant_extras
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            END IF;
        END $$;
        """
    )

    op.drop_column("participants", "local_context")
    op.drop_column("participants", "fun_fact")

    op.add_column(
        "participants",
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("industry", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("company", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("summary", sa.Text(), nullable=True),
    )

    op.add_column(
        "company_dna",
        sa.Column("tone", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "company_dna",
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "revealed_phases",
            ARRAY(TEXT()),
            server_default=sa.text("'{}'::text[]"),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "workshop_data",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column("participant_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "duration_mins",
            sa.Integer(),
            server_default=sa.text("90"),
            nullable=True,
        ),
    )

    op.drop_column("company_dna", "raw_markdown")
