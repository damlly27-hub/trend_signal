from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient


def create_trend(client: TestClient, name: str = "포켓몬 카드") -> dict[str, Any]:
    response = client.post(
        "/trends",
        json={
            "name": name,
            "category": "PRODUCT",
            "description": "SNS 및 검색 트렌드를 추적하기 위한 후보",
            "aliases": ["포켓몬카드", "Pokemon Card", "포켓몬 TCG"],
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_create_trend_with_aliases(client: TestClient) -> None:
    trend = create_trend(client)

    assert trend["name"] == "포켓몬 카드"
    assert trend["category"] == "PRODUCT"
    assert trend["status"] == "ACTIVE"
    assert [alias["alias"] for alias in trend["aliases"]] == [
        "포켓몬카드",
        "Pokemon Card",
        "포켓몬 TCG",
    ]


def test_duplicate_trend_name_returns_conflict(client: TestClient) -> None:
    create_trend(client)

    response = client.post("/trends", json={"name": "포켓몬 카드"})

    assert response.status_code == 409


def test_add_alias(client: TestClient) -> None:
    trend = create_trend(client)

    response = client.post(
        f"/trends/{trend['id']}/aliases",
        json={"alias": "포켓몬 카드게임"},
    )

    assert response.status_code == 201
    assert response.json()["alias"] == "포켓몬 카드게임"


def test_duplicate_normalized_alias_returns_conflict(client: TestClient) -> None:
    trend = create_trend(client)

    response = client.post(
        f"/trends/{trend['id']}/aliases",
        json={"alias": "  POKEMON   CARD  "},
    )

    assert response.status_code == 409


def test_get_missing_trend_returns_not_found(client: TestClient) -> None:
    response = client.get(f"/trends/{uuid4()}")

    assert response.status_code == 404


def test_list_trends(client: TestClient) -> None:
    create_trend(client, "포켓몬 카드")
    create_trend(client, "버터떡")

    response = client.get("/trends")

    assert response.status_code == 200
    assert [trend["name"] for trend in response.json()] == ["포켓몬 카드", "버터떡"]


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}

