from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.collection.contracts import (
    AliasCollectionError,
    CollectionRequest,
    CollectionResult,
    CollectionStatus,
    ObservationData,
    ProviderName,
)
from app.collection.fixture import FixtureCollector
from app.models.trend import TrendCategory, TrendStatus
from app.services.collection import CollectionService
from app.services.exceptions import TrendNotCollectibleError


def create_trend(client: TestClient, name: str = "포켓몬 카드") -> dict[str, Any]:
    response = client.post(
        "/trends",
        json={
            "name": name,
            "category": "PRODUCT",
            "aliases": ["포켓몬카드", "Pokemon Card", "포켓몬 TCG"],
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def make_request() -> CollectionRequest:
    return CollectionRequest(
        trend_id=uuid4(),
        trend_name="포켓몬 카드",
        category=TrendCategory.PRODUCT,
        aliases=("포켓몬카드", "Pokemon Card", "포켓몬 TCG"),
        requested_at=datetime.now(UTC),
        provider=ProviderName.FIXTURE,
    )


def test_active_trend_builds_request_with_aliases(
    client: TestClient, db_session: Session
) -> None:
    trend_payload = create_trend(client)
    service = CollectionService(db_session)
    loaded = service.trends.get(UUID(trend_payload["id"]))
    assert loaded is not None

    request = service.build_request(loaded, ProviderName.FIXTURE)

    assert request.trend_name == "포켓몬 카드"
    assert request.aliases == ("포켓몬카드", "Pokemon Card", "포켓몬 TCG")
    assert request.provider is ProviderName.FIXTURE


@pytest.mark.parametrize("trend_status", [TrendStatus.PAUSED, TrendStatus.ARCHIVED])
def test_inactive_trend_cannot_build_request(
    client: TestClient, db_session: Session, trend_status: TrendStatus
) -> None:
    trend_payload = create_trend(client, f"status-{trend_status.value}")
    service = CollectionService(db_session)
    trend = service.trends.get(UUID(trend_payload["id"]))
    assert trend is not None
    trend.status = trend_status
    db_session.commit()

    with pytest.raises(TrendNotCollectibleError):
        service.build_request(trend, ProviderName.FIXTURE)


def test_fixture_collector_is_deterministic() -> None:
    collector = FixtureCollector()

    first = collector.collect(make_request())
    second = collector.collect(make_request())

    assert first.status is CollectionStatus.SUCCEEDED
    assert first.observation == second.observation == ObservationData(
        video_count=25,
        new_video_count=8,
        unique_creator_count=17,
        total_views=125_000,
        total_comments=1_800,
        total_likes=9_200,
        search_ratio=18.5,
    )
    assert first.used_aliases == make_request().aliases
    assert first.is_fixture is True


def test_collection_result_can_represent_partial_alias_failure() -> None:
    request = make_request()
    result = CollectionResult(
        provider=ProviderName.YOUTUBE,
        trend_id=request.trend_id,
        collected_at=datetime.now(UTC),
        observation=ObservationData(video_count=1),
        status=CollectionStatus.PARTIAL,
        used_aliases=(request.aliases[0],),
        errors=(
            AliasCollectionError(
                alias=request.aliases[1],
                code="TIMEOUT",
                message="alias request timed out",
                retryable=True,
            ),
        ),
    )

    assert result.status is CollectionStatus.PARTIAL
    assert result.errors[0].alias == "Pokemon Card"
    assert result.observation is not None


def test_collect_fixture_appends_and_lists_observations(client: TestClient) -> None:
    trend = create_trend(client)

    first = client.post(f"/trends/{trend['id']}/collect-fixture")
    second = client.post(f"/trends/{trend['id']}/collect-fixture")
    response = client.get(f"/trends/{trend['id']}/observations")

    assert first.status_code == second.status_code == 201
    observations = cast(list[dict[str, Any]], response.json())
    assert response.status_code == 200
    assert len(observations) == 2
    assert observations[0]["id"] != observations[1]["id"]
    assert observations[0]["collection_run_id"] != observations[1]["collection_run_id"]
    assert all(item["source"] == "FIXTURE" for item in observations)
    assert all(item["is_fixture"] is True for item in observations)
    assert all(item["collected_at"] for item in observations)
    assert [item["total_views"] for item in observations] == [125_000, 125_000]


def test_collect_missing_trend_returns_not_found(client: TestClient) -> None:
    response = client.post(f"/trends/{uuid4()}/collect-fixture")

    assert response.status_code == 404


def test_list_observations_for_missing_trend_returns_not_found(client: TestClient) -> None:
    response = client.get(f"/trends/{uuid4()}/observations")

    assert response.status_code == 404

