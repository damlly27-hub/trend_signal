from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection import CollectionRun, Observation, SearchTrendObservation


class CollectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_run(self, run: CollectionRun) -> CollectionRun:
        self.db.add(run)
        return run

    def add_observation(self, observation: Observation) -> Observation:
        self.db.add(observation)
        return observation

    def add_search_trend_observation(
        self, observation: SearchTrendObservation
    ) -> SearchTrendObservation:
        self.db.add(observation)
        return observation

    def list_observations(self, trend_id: UUID) -> Sequence[Observation]:
        statement = (
            select(Observation)
            .where(Observation.trend_id == trend_id)
            .order_by(Observation.collected_at, Observation.created_at, Observation.id)
        )
        return self.db.scalars(statement).all()

    def list_search_trend_observations(
        self,
        trend_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sequence[SearchTrendObservation]:
        statement = select(SearchTrendObservation).where(
            SearchTrendObservation.trend_id == trend_id
        )
        if start_date is not None:
            statement = statement.where(SearchTrendObservation.period >= start_date)
        if end_date is not None:
            statement = statement.where(SearchTrendObservation.period <= end_date)
        statement = statement.order_by(
            SearchTrendObservation.period,
            SearchTrendObservation.collected_at,
            SearchTrendObservation.id,
        )
        return self.db.scalars(statement).all()

