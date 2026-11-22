"""Create trends and trend aliases.

Revision ID: 20261122_0001
Revises: None
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261122_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

trend_category = postgresql.ENUM(
    "FOOD", "BEAUTY", "GAME", "MEME", "PRODUCT", "ENTERTAINMENT", "OTHER",
    name="trend_category",
    create_type=False,
)
trend_status = postgresql.ENUM(
    "ACTIVE", "PAUSED", "ARCHIVED", name="trend_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    trend_category.create(bind, checkfirst=True)
    trend_status.create(bind, checkfirst=True)

    op.create_table(
        "trends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", trend_category, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", trend_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_trends_name"),
    )
    op.create_table(
        "trend_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trend_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trend_id"], ["trends.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trend_id", "normalized_alias", name="uq_trend_alias_normalized"),
    )
    op.create_index("ix_trend_aliases_trend_id", "trend_aliases", ["trend_id"])


def downgrade() -> None:
    op.drop_index("ix_trend_aliases_trend_id", table_name="trend_aliases")
    op.drop_table("trend_aliases")
    op.drop_table("trends")
    trend_status.drop(op.get_bind(), checkfirst=True)
    trend_category.drop(op.get_bind(), checkfirst=True)

