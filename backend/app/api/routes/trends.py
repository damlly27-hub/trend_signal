from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import DbSession, NaverCollector
from app.collection.naver import (
    NaverAuthenticationError,
    NaverCollectorError,
    NaverConfigurationError,
    NaverMalformedResponseError,
    NaverNetworkError,
    NaverProviderError,
    NaverRateLimitError,
    NaverValidationError,
)
from app.schemas.collection import (
    NaverCollectionCreate,
    NaverCollectionSummary,
    ObservationRead,
    SearchTrendObservationRead,
)
from app.schemas.trend import AliasCreate, AliasRead, TrendCreate, TrendRead
from app.services.collection import CollectionService
from app.services.exceptions import (
    CollectionFailedError,
    DuplicateAliasError,
    DuplicateTrendError,
    TrendNotCollectibleError,
    TrendNotFoundError,
)
from app.services.trend import TrendService

router = APIRouter(prefix="/trends", tags=["trends"])


@router.post(
    "/{trend_id}/collect/naver-search-trend",
    response_model=NaverCollectionSummary,
    status_code=status.HTTP_201_CREATED,
)
def collect_naver_search_trend(
    trend_id: UUID,
    payload: NaverCollectionCreate,
    db: DbSession,
    collector: NaverCollector,
) -> NaverCollectionSummary:
    try:
        run, observations = CollectionService(db).collect_naver_search_trend(
            trend_id,
            payload.start_date,
            payload.end_date,
            payload.time_unit,
            collector,
        )
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TrendNotCollectibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NaverConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except NaverValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except NaverRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    except (
        NaverAuthenticationError,
        NaverProviderError,
        NaverNetworkError,
        NaverMalformedResponseError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except NaverCollectorError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return NaverCollectionSummary(
        trend_id=trend_id,
        provider="NAVER_SEARCH_TREND",
        collection_run_id=run.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        observation_count=len(observations),
        status="SUCCEEDED",
    )


@router.get(
    "/{trend_id}/search-trend-observations",
    response_model=list[SearchTrendObservationRead],
)
def list_search_trend_observations(
    trend_id: UUID,
    db: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SearchTrendObservationRead]:
    try:
        observations = CollectionService(db).list_search_trend_observations(
            trend_id, start_date, end_date
        )
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [SearchTrendObservationRead.model_validate(item) for item in observations]


@router.post(
    "/{trend_id}/collect-fixture",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
)
def collect_fixture(trend_id: UUID, db: DbSession) -> ObservationRead:
    try:
        return ObservationRead.model_validate(CollectionService(db).collect_fixture(trend_id))
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TrendNotCollectibleError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CollectionFailedError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/{trend_id}/observations", response_model=list[ObservationRead])
def list_observations(trend_id: UUID, db: DbSession) -> list[ObservationRead]:
    try:
        return [
            ObservationRead.model_validate(observation)
            for observation in CollectionService(db).list_observations(trend_id)
        ]
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=TrendRead, status_code=status.HTTP_201_CREATED)
def create_trend(payload: TrendCreate, db: DbSession) -> TrendRead:
    try:
        return TrendRead.model_validate(TrendService(db).create_trend(payload))
    except DuplicateTrendError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DuplicateAliasError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[TrendRead])
def list_trends(db: DbSession) -> list[TrendRead]:
    return [TrendRead.model_validate(trend) for trend in TrendService(db).list_trends()]


@router.get("/{trend_id}", response_model=TrendRead)
def get_trend(trend_id: UUID, db: DbSession) -> TrendRead:
    try:
        return TrendRead.model_validate(TrendService(db).get_trend(trend_id))
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{trend_id}/aliases",
    response_model=AliasRead,
    status_code=status.HTTP_201_CREATED,
)
def create_alias(trend_id: UUID, payload: AliasCreate, db: DbSession) -> AliasRead:
    try:
        return AliasRead.model_validate(TrendService(db).add_alias(trend_id, payload))
    except TrendNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateAliasError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

