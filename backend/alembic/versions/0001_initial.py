"""initial schema: trips, itineraries, agent_runs, preferences

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JsonType = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", sa.String(64), index=True, nullable=True),
        sa.Column("raw_query", sa.String(1024), nullable=False),
        sa.Column("origin", sa.String(120), nullable=False),
        sa.Column("destination", sa.String(120), nullable=False),
        sa.Column("days", sa.Integer, nullable=False),
        sa.Column("budget_cap", sa.Float, nullable=False),
        sa.Column("currency", sa.String(8), server_default="INR"),
        sa.Column("status", sa.String(32), server_default="completed"),
    )
    op.create_table(
        "itineraries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trips.id", ondelete="CASCADE")),
        sa.Column("total_cost", sa.Float, nullable=False),
        sa.Column("within_budget", sa.Boolean, nullable=False),
        sa.Column("data", JsonType, nullable=False),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trips.id", ondelete="CASCADE")),
        sa.Column("agent", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("detail", sa.String(512), nullable=True),
    )
    op.create_table(
        "preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(64), index=True, nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("preferences")
    op.drop_table("agent_runs")
    op.drop_table("itineraries")
    op.drop_table("trips")
