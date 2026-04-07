"""add avatar and voice ids to sessions

Revision ID: 20260407_0003
Revises: 20260406_0002
Create Date: 2026-04-07

Adds avatar_id and voice_id columns to sessions table for LiveAvatar selection
and app-managed voice prompts.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_0003"
down_revision = "20260406_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add avatar_id and voice_id columns to sessions table."""
    op.add_column(
        "sessions",
        sa.Column(
            "avatar_id",
            sa.String(100),
            nullable=True,
            comment="LiveAvatar avatar ID selected during Phase 0 setup",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "voice_id",
            sa.String(100),
            nullable=True,
            comment="ElevenLabs voice ID for workshop guide speech",
        ),
    )


def downgrade() -> None:
    """Remove avatar_id and voice_id columns."""
    op.drop_column("sessions", "voice_id")
    op.drop_column("sessions", "avatar_id")
