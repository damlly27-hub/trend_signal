from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.models.trend import TrendCategory


class ProviderName(StrEnum):
    FIXTURE = "FIXTURE"
    YOUTUBE = "YOUTUBE"
    NAVER_SEARCH_TREND = "NAVER_SEARCH_TREND"


class CollectionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CollectionRequest:
    trend_id: UUID
    trend_name: str
    category: TrendCategory
    aliases: tuple[str, ...]
    requested_at: datetime
    provider: ProviderName
    start_date: date | None = None
    end_date: date | None = None
    time_unit: str | None = None


@dataclass(frozen=True)
class ObservationData:
    video_count: int | None = None
    new_video_count: int | None = None
    unique_creator_count: int | None = None
    total_views: int | None = None
    total_comments: int | None = None
    total_likes: int | None = None
    search_ratio: float | None = None


@dataclass(frozen=True)
class AliasCollectionError:
    alias: str
    code: str
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class SearchTrendPoint:
    period: date
    ratio: Decimal


@dataclass(frozen=True)
class CollectionResult:
    provider: ProviderName
    trend_id: UUID
    collected_at: datetime
    observation: ObservationData | None
    status: CollectionStatus
    used_aliases: tuple[str, ...]
    errors: tuple[AliasCollectionError, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    is_fixture: bool = False
    search_trend_points: tuple[SearchTrendPoint, ...] = field(default_factory=tuple)
    group_name: str | None = None


class Collector(Protocol):
    provider: ProviderName

    def collect(self, request: CollectionRequest) -> CollectionResult: ...

