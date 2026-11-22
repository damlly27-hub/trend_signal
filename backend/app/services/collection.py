from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.collection.contracts import (
    CollectionRequest,
    CollectionResult,
    CollectionStatus,
    ProviderName,
)
from app.collection.fixture import FixtureCollector
from app.collection.naver import NaverSearchTrendCollector
from app.models.collection import (
    CollectionRun,
    Observation,
    RunStatus,
    SearchTrendObservation,
)
from app.models.trend import Trend, TrendStatus
from app.repositories.collection import CollectionRepository
from app.repositories.trend import TrendRepository
from app.services.exceptions import (
    CollectionFailedError,
    TrendNotCollectibleError,
    TrendNotFoundError,
)


class CollectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trends = TrendRepository(db)
        self.collections = CollectionRepository(db)

    def build_request(
        self,
        trend: Trend,
        provider: ProviderName,
        requested_at: datetime | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        time_unit: str | None = None,
    ) -> CollectionRequest:
        if trend.status is not TrendStatus.ACTIVE:
            raise TrendNotCollectibleError(
                f"Trend {trend.id} is {trend.status.value}; only ACTIVE trends can be collected"
            )
        return CollectionRequest(
            trend_id=trend.id,
            trend_name=trend.name,
            category=trend.category,
            aliases=tuple(alias.alias for alias in trend.aliases),
            requested_at=requested_at or datetime.now(UTC),
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
        )

    def collect_fixture(self, trend_id: UUID) -> Observation:
        trend = self._get_trend(trend_id)
        request = self.build_request(trend, ProviderName.FIXTURE)
        result = FixtureCollector().collect(request)
        return self._persist_result(request, result)

    def list_observations(self, trend_id: UUID) -> Sequence[Observation]:
        self._get_trend(trend_id)
        return self.collections.list_observations(trend_id)

    def collect_naver_search_trend(
        self,
        trend_id: UUID,
        start_date: date,
        end_date: date,
        time_unit: str,
        collector: NaverSearchTrendCollector,
    ) -> tuple[CollectionRun, Sequence[SearchTrendObservation]]:
        trend = self._get_trend(trend_id)
        request = self.build_request(
            trend,
            ProviderName.NAVER_SEARCH_TREND,
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
        )
        result = collector.collect(request)
        return self._persist_search_trend_result(request, result)

    def list_search_trend_observations(
        self,
        trend_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sequence[SearchTrendObservation]:
        self._get_trend(trend_id)
        return self.collections.list_search_trend_observations(
            trend_id, start_date, end_date
        )

    def _get_trend(self, trend_id: UUID) -> Trend:
        trend = self.trends.get(trend_id)
        if trend is None:
            raise TrendNotFoundError(f"Trend not found: {trend_id}")
        return trend

    def _persist_result(
        self, request: CollectionRequest, result: CollectionResult
    ) -> Observation:
        if result.trend_id != request.trend_id or result.provider != request.provider:
            raise CollectionFailedError("Collector result does not match its request")
        if result.status is CollectionStatus.FAILED or result.observation is None:
            raise CollectionFailedError("Collector returned no persistable observation")

        run = CollectionRun(
            trend_id=request.trend_id,
            provider=result.provider.value,
            requested_at=request.requested_at,
            collected_at=result.collected_at,
            status=RunStatus(result.status.value),
            error_summary="; ".join(error.message for error in result.errors) or None,
            is_fixture=result.is_fixture,
        )
        self.collections.add_run(run)
        self.db.flush()
        data = result.observation
        observation = Observation(
            trend_id=request.trend_id,
            collection_run_id=run.id,
            source=result.provider.value,
            collected_at=result.collected_at,
            video_count=data.video_count,
            new_video_count=data.new_video_count,
            unique_creator_count=data.unique_creator_count,
            total_views=data.total_views,
            total_comments=data.total_comments,
            total_likes=data.total_likes,
            search_ratio=data.search_ratio,
            is_fixture=result.is_fixture,
        )
        self.collections.add_observation(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def _persist_search_trend_result(
        self, request: CollectionRequest, result: CollectionResult
    ) -> tuple[CollectionRun, Sequence[SearchTrendObservation]]:
        if result.trend_id != request.trend_id or result.provider != request.provider:
            raise CollectionFailedError("Collector result does not match its request")
        if result.status is CollectionStatus.FAILED:
            raise CollectionFailedError("Collector returned a failed result")
        if request.start_date is None or request.end_date is None or request.time_unit is None:
            raise CollectionFailedError("Collection request is missing its window metadata")

        run = CollectionRun(
            trend_id=request.trend_id,
            provider=result.provider.value,
            requested_at=request.requested_at,
            collected_at=result.collected_at,
            status=RunStatus(result.status.value),
            error_summary="; ".join(error.message for error in result.errors) or None,
            request_start_date=request.start_date,
            request_end_date=request.end_date,
            time_unit=request.time_unit,
            group_name=result.group_name,
            keywords=list(result.used_aliases),
            is_fixture=False,
        )
        self.collections.add_run(run)
        self.db.flush()
        observations = [
            SearchTrendObservation(
                trend_id=request.trend_id,
                collection_run_id=run.id,
                provider=result.provider.value,
                period=point.period,
                ratio=point.ratio,
                collected_at=result.collected_at,
                is_fixture=False,
            )
            for point in result.search_trend_points
        ]
        for observation in observations:
            self.collections.add_search_trend_observation(observation)
        self.db.commit()
        return run, observations

