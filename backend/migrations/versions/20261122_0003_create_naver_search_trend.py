"""Create NAVER Search Trend period observations.

Revision ID: 20261122_0003
Revises: 20261122_0002
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_0003"
down_revision: str | Sequence[str] | None = "20261122_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("collection_runs", sa.Column("request_start_date", sa.Date(), nullable=True))
    op.add_column("collection_runs", sa.Column("request_end_date", sa.Date(), nullable=True))
    op.add_column("collection_runs", sa.Column("time_unit", sa.String(10), nullable=True))
    op.add_column("collection_runs", sa.Column("group_name", sa.String(200), nullable=True))
    op.add_column("collection_runs", sa.Column("keywords", sa.JSON(), nullable=True))
    op.create_table(
        "search_trend_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trend_id", sa.Uuid(), nullable=False),
        sa.Column("collection_run_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(10, 5), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint(
            "collection_run_id", "period", name="uq_search_trend_run_period"
        ),
    )
    op.create_index(
        "ix_search_trend_observations_trend_id",
        "search_trend_observations",
        ["trend_id"],
    )
    op.create_index(
        "ix_search_trend_observations_collection_run_id",
        "search_trend_observations",
        ["collection_run_id"],
    )
    op.create_index(
        "ix_search_trend_observations_period",
        "search_trend_observations",
        ["period"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_search_trend_observations_period", table_name="search_trend_observations"
    )
    op.drop_index(
        "ix_search_trend_observations_collection_run_id",
        table_name="search_trend_observations",
    )
    op.drop_index(
        "ix_search_trend_observations_trend_id",
        table_name="search_trend_observations",
    )
    op.drop_table("search_trend_observations")
    op.drop_column("collection_runs", "keywords")
    op.drop_column("collection_runs", "group_name")
    op.drop_column("collection_runs", "time_unit")
    op.drop_column("collection_runs", "request_end_date")
    op.drop_column("collection_runs", "request_start_date")
