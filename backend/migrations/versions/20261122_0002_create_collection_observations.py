"""Create collection runs and append-only observations.

Revision ID: 20261122_0002
Revises: 20261122_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261122_0002"
down_revision: str | Sequence[str] | None = "20261122_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_status = postgresql.ENUM(
        "SUCCEEDED",
        "PARTIAL",
        "FAILED",
        name="collection_run_status",
        create_type=False,
    )
    run_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trend_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("is_fixture", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trend_id"], ["trends.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_runs_trend_id", "collection_runs", ["trend_id"])
    op.create_table(
        "observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trend_id", sa.Uuid(), nullable=False),
        sa.Column("collection_run_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("video_count", sa.Integer(), nullable=True),
        sa.Column("new_video_count", sa.Integer(), nullable=True),
        sa.Column("unique_creator_count", sa.Integer(), nullable=True),
        sa.Column("total_views", sa.BigInteger(), nullable=True),
        sa.Column("total_comments", sa.BigInteger(), nullable=True),
        sa.Column("total_likes", sa.BigInteger(), nullable=True),
        sa.Column("search_ratio", sa.Float(), nullable=True),
        sa.Column("is_fixture", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_run_id"], ["collection_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["trend_id"], ["trends.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observations_trend_id", "observations", ["trend_id"])
    op.create_index(
        "ix_observations_collection_run_id", "observations", ["collection_run_id"]
    )
    op.create_index("ix_observations_collected_at", "observations", ["collected_at"])


def downgrade() -> None:
    op.drop_index("ix_observations_collected_at", table_name="observations")
    op.drop_index("ix_observations_collection_run_id", table_name="observations")
    op.drop_index("ix_observations_trend_id", table_name="observations")
    op.drop_table("observations")
    op.drop_index("ix_collection_runs_trend_id", table_name="collection_runs")
    op.drop_table("collection_runs")
    postgresql.ENUM(name="collection_run_status").drop(op.get_bind(), checkfirst=True)
