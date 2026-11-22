from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.trend import Trend, TrendAlias
from app.repositories.trend import TrendRepository
from app.schemas.trend import AliasCreate, TrendCreate
from app.services.exceptions import DuplicateAliasError, DuplicateTrendError, TrendNotFoundError
from app.services.normalization import normalize_alias


class TrendService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TrendRepository(db)

    def create_trend(self, payload: TrendCreate) -> Trend:
        normalized_aliases = [normalize_alias(alias) for alias in payload.aliases]
        if len(normalized_aliases) != len(set(normalized_aliases)):
            raise DuplicateAliasError("Duplicate aliases are not allowed within a trend")

        trend = Trend(
            name=payload.name,
            category=payload.category,
            description=payload.description,
        )
        trend.aliases = [
            TrendAlias(alias=alias, normalized_alias=normalized)
            for alias, normalized in zip(payload.aliases, normalized_aliases, strict=True)
        ]
        self.repository.add(trend)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateTrendError(f"Trend name already exists: {payload.name}") from exc
        self.db.refresh(trend)
        return self.get_trend(trend.id)

    def get_trend(self, trend_id: UUID) -> Trend:
        trend = self.repository.get(trend_id)
        if trend is None:
            raise TrendNotFoundError(f"Trend not found: {trend_id}")
        return trend

    def list_trends(self) -> Sequence[Trend]:
        return self.repository.list()

    def add_alias(self, trend_id: UUID, payload: AliasCreate) -> TrendAlias:
        self.get_trend(trend_id)
        trend_alias = TrendAlias(
            trend_id=trend_id,
            alias=payload.alias,
            normalized_alias=normalize_alias(payload.alias),
        )
        self.repository.add_alias(trend_alias)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateAliasError(
                f"Alias already exists for trend {trend_id}: {payload.alias}"
            ) from exc
        self.db.refresh(trend_alias)
        return trend_alias

