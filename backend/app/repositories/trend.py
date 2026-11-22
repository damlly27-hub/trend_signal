from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.trend import Trend, TrendAlias


class TrendRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, trend: Trend) -> Trend:
        self.db.add(trend)
        return trend

    def add_alias(self, trend_alias: TrendAlias) -> TrendAlias:
        self.db.add(trend_alias)
        return trend_alias

    def get(self, trend_id: UUID) -> Trend | None:
        statement = (
            select(Trend).options(selectinload(Trend.aliases)).where(Trend.id == trend_id)
        )
        return self.db.scalar(statement)

    def list(self) -> Sequence[Trend]:
        statement = select(Trend).options(selectinload(Trend.aliases)).order_by(Trend.created_at)
        return self.db.scalars(statement).all()

