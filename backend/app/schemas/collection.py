from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trend_id: UUID
    collection_run_id: UUID
    source: str
    collected_at: datetime
    video_count: int | None
    new_video_count: int | None
    unique_creator_count: int | None
    total_views: int | None
    total_comments: int | None
    total_likes: int | None
    search_ratio: float | None
    is_fixture: bool
    created_at: datetime


class NaverCollectionCreate(BaseModel):
    start_date: date
    end_date: date
    time_unit: Literal["date", "week", "month"] = "date"


class NaverCollectionSummary(BaseModel):
    trend_id: UUID
    provider: Literal["NAVER_SEARCH_TREND"]
    collection_run_id: UUID
    start_date: date
    end_date: date
    observation_count: int
    status: Literal["SUCCEEDED"]


class SearchTrendObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trend_id: UUID
    collection_run_id: UUID
    provider: str
    period: date
    ratio: Decimal
    collected_at: datetime
    is_fixture: bool
    created_at: datetime

