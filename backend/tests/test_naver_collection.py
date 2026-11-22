import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_naver_search_trend_collector
from app.collection.contracts import CollectionRequest, ProviderName
from app.collection.naver import (
    NaverAuthenticationError,
    NaverConfigurationError,
    NaverMalformedResponseError,
    NaverNetworkError,
    NaverProviderError,
    NaverRateLimitError,
    NaverSearchTrendCollector,
    NaverValidationError,
    build_keywords,
)
from app.main import app
from app.models.collection import CollectionRun, SearchTrendObservation
from app.models.trend import Trend, TrendCategory, TrendStatus


def make_request(aliases: tuple[str, ...] = ("포켓몬카드", "Pokemon Card")) -> CollectionRequest:
    return CollectionRequest(
        trend_id=uuid4(),
        trend_name="포켓몬 카드",
        category=TrendCategory.PRODUCT,
        aliases=aliases,
        requested_at=datetime.now(UTC),
        provider=ProviderName.NAVER_SEARCH_TREND,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 2),
        time_unit="date",
    )


def response_body() -> dict[str, object]:
    return {
        "startDate": "2026-10-01",
        "endDate": "2026-10-02",
        "timeUnit": "date",
        "results": [
            {
                "title": "포켓몬 카드",
                "keywords": ["포켓몬 카드", "포켓몬카드", "Pokemon Card"],
                "data": [
                    {"period": "2026-10-01", "ratio": 42.12345},
                    {"period": "2026-10-02", "ratio": 100},
                ],
            }
        ],
    }


def make_collector(handler: httpx.MockTransport) -> NaverSearchTrendCollector:
    return NaverSearchTrendCollector(
        client_id="test-client-id",
        client_secret="test-client-secret",
        base_url="https://naver.test",
        timeout_seconds=1,
        client=httpx.Client(transport=handler),
    )


def create_trend(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/trends",
        json={
            "name": "포켓몬 카드",
            "category": "PRODUCT",
            "aliases": ["포켓몬카드", "Pokemon Card", "포켓몬 카드"],
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_naver_payload_includes_name_aliases_and_deduplicates() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(cast(dict[str, Any], json.loads(request.content)))
        return httpx.Response(200, json=response_body())

    result = make_collector(httpx.MockTransport(handler)).collect(
        make_request(("포켓몬카드", "포켓몬 카드", "Pokemon Card"))
    )

    group = captured["keywordGroups"][0]
    assert group == {
        "groupName": "포켓몬 카드",
        "keywords": ["포켓몬 카드", "포켓몬카드", "Pokemon Card"],
    }
    assert captured["timeUnit"] == "date"
    assert result.search_trend_points[0].ratio == Decimal("42.12345")


def test_keyword_limit_is_validated_without_truncation() -> None:
    request = make_request(tuple(f"alias-{index}" for index in range(20)))

    with pytest.raises(NaverValidationError, match="at most 20"):
        build_keywords(request)


def test_missing_credentials_are_lazy_configuration_error() -> None:
    collector = NaverSearchTrendCollector(None, None, "https://naver.test", 1)

    with pytest.raises(NaverConfigurationError):
        collector.collect(make_request())


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, NaverAuthenticationError),
        (403, NaverAuthenticationError),
        (429, NaverRateLimitError),
        (500, NaverProviderError),
    ],
)
def test_provider_http_errors_are_classified(
    status_code: int, error_type: type[Exception]
) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status_code, text="test-client-secret")
    )

    with pytest.raises(error_type, match="NAVER") as captured:
        make_collector(transport).collect(make_request())
    assert "test-client-secret" not in str(captured.value)


def test_timeout_is_safe_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("test-client-secret", request=request)

    with pytest.raises(NaverNetworkError) as captured:
        make_collector(httpx.MockTransport(handler)).collect(make_request())
    assert "test-client-secret" not in str(captured.value)


def test_malformed_response_is_rejected() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"results": []}))

    with pytest.raises(NaverMalformedResponseError):
        make_collector(transport).collect(make_request())


def test_naver_api_saves_multiple_periods_and_run_metadata(
    client: TestClient, db_session: Session
) -> None:
    trend = create_trend(client)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=response_body()))
    collector = make_collector(transport)
    app.dependency_overrides[get_naver_search_trend_collector] = lambda: collector

    response = client.post(
        f"/trends/{trend['id']}/collect/naver-search-trend",
        json={"start_date": "2026-10-01", "end_date": "2026-10-02"},
    )

    assert response.status_code == 201
    assert response.json()["observation_count"] == 2
    run = db_session.scalar(select(CollectionRun))
    assert run is not None
    assert run.request_start_date == date(2026, 10, 1)
    assert run.request_end_date == date(2026, 10, 2)
    assert run.time_unit == "date"
    assert run.group_name == "포켓몬 카드"
    assert run.keywords == ["포켓몬 카드", "포켓몬카드", "Pokemon Card"]
    observations = db_session.scalars(select(SearchTrendObservation)).all()
    assert [item.ratio for item in observations] == [Decimal("42.12345"), Decimal("100.00000")]
    assert all(item.collection_run_id == run.id for item in observations)
    assert all(item.is_fixture is False for item in observations)

    listed = client.get(f"/trends/{trend['id']}/search-trend-observations")
    assert listed.status_code == 200
    assert len(listed.json()) == 2


def test_same_period_from_two_runs_is_append_only(
    client: TestClient, db_session: Session
) -> None:
    trend = create_trend(client)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=response_body()))
    app.dependency_overrides[get_naver_search_trend_collector] = lambda: make_collector(
        transport
    )
    url = f"/trends/{trend['id']}/collect/naver-search-trend"
    payload = {"start_date": "2026-10-01", "end_date": "2026-10-02"}

    assert client.post(url, json=payload).status_code == 201
    assert client.post(url, json=payload).status_code == 201

    observations = db_session.scalars(select(SearchTrendObservation)).all()
    assert len(observations) == 4
    assert len({item.collection_run_id for item in observations}) == 2


def test_only_active_trend_can_collect_naver(
    client: TestClient, db_session: Session
) -> None:
    trend = create_trend(client)
    model = db_session.get(Trend, UUID(trend["id"]))
    assert model is not None
    model.status = TrendStatus.PAUSED
    db_session.commit()
    transport = httpx.MockTransport(lambda _: pytest.fail("HTTP must not be called"))
    app.dependency_overrides[get_naver_search_trend_collector] = lambda: make_collector(
        transport
    )

    response = client.post(
        f"/trends/{trend['id']}/collect/naver-search-trend",
        json={"start_date": "2026-10-01", "end_date": "2026-10-02"},
    )

    assert response.status_code == 409


def test_missing_credentials_api_response_does_not_expose_secret(client: TestClient) -> None:
    trend = create_trend(client)
    app.dependency_overrides[get_naver_search_trend_collector] = lambda: (
        NaverSearchTrendCollector(None, None, "https://naver.test", 1)
    )

    response = client.post(
        f"/trends/{trend['id']}/collect/naver-search-trend",
        json={"start_date": "2026-10-01", "end_date": "2026-10-02"},
    )

    assert response.status_code == 503
    assert "secret" not in response.text.casefold()
