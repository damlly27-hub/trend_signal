from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.collection.naver import NaverSearchTrendCollector
from app.core.config import get_settings
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_naver_search_trend_collector() -> NaverSearchTrendCollector:
    settings = get_settings()
    return NaverSearchTrendCollector(
        client_id=settings.naver_api_hub_client_id,
        client_secret=settings.naver_api_hub_client_secret,
        base_url=settings.naver_api_hub_base_url,
        timeout_seconds=settings.collector_request_timeout_seconds,
    )


NaverCollector = Annotated[
    NaverSearchTrendCollector, Depends(get_naver_search_trend_collector)
]

