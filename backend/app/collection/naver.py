from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import httpx

from app.collection.contracts import (
    CollectionRequest,
    CollectionResult,
    CollectionStatus,
    ProviderName,
    SearchTrendPoint,
)

NAVER_SEARCH_TREND_PATH = "/search-trend/v1/search"
MAX_KEYWORDS_PER_GROUP = 20


class NaverCollectorError(Exception):
    code = "NAVER_PROVIDER_ERROR"
    retryable = False


class NaverConfigurationError(NaverCollectorError):
    code = "NAVER_CONFIGURATION_ERROR"


class NaverValidationError(NaverCollectorError):
    code = "NAVER_VALIDATION_ERROR"


class NaverAuthenticationError(NaverCollectorError):
    code = "NAVER_AUTHENTICATION_ERROR"


class NaverRateLimitError(NaverCollectorError):
    code = "NAVER_RATE_LIMIT"
    retryable = True


class NaverProviderError(NaverCollectorError):
    code = "NAVER_PROVIDER_ERROR"
    retryable = True


class NaverNetworkError(NaverCollectorError):
    code = "NAVER_NETWORK_ERROR"
    retryable = True


class NaverMalformedResponseError(NaverCollectorError):
    code = "NAVER_MALFORMED_RESPONSE"


def build_keywords(request: CollectionRequest) -> tuple[str, ...]:
    keywords = tuple(dict.fromkeys((request.trend_name, *request.aliases)))
    if len(keywords) > MAX_KEYWORDS_PER_GROUP:
        raise NaverValidationError(
            f"NAVER Search Trend allows at most {MAX_KEYWORDS_PER_GROUP} keywords per group"
        )
    return keywords


class NaverSearchTrendCollector:
    provider = ProviderName.NAVER_SEARCH_TREND

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        base_url: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = client

    def collect(self, request: CollectionRequest) -> CollectionResult:
        if not self._client_id or not self._client_secret:
            raise NaverConfigurationError("NAVER API HUB credentials are not configured")
        if request.provider is not self.provider:
            raise NaverValidationError("Collector provider does not match request provider")
        if request.start_date is None or request.end_date is None or request.time_unit is None:
            raise NaverValidationError("start_date, end_date, and time_unit are required")
        if request.start_date > request.end_date:
            raise NaverValidationError("start_date must be on or before end_date")
        if request.time_unit not in {"date", "week", "month"}:
            raise NaverValidationError("time_unit must be date, week, or month")

        keywords = build_keywords(request)
        payload: dict[str, object] = {
            "startDate": request.start_date.isoformat(),
            "endDate": request.end_date.isoformat(),
            "timeUnit": request.time_unit,
            "keywordGroups": [
                {"groupName": request.trend_name, "keywords": list(keywords)}
            ],
        }
        headers = {
            "X-NCP-APIGW-API-KEY-ID": self._client_id,
            "X-NCP-APIGW-API-KEY": self._client_secret,
            "Content-Type": "application/json",
        }
        response = self._post(payload, headers)
        points = self._parse_response(response, request)
        return CollectionResult(
            provider=self.provider,
            trend_id=request.trend_id,
            collected_at=datetime.now(UTC),
            observation=None,
            status=CollectionStatus.SUCCEEDED,
            used_aliases=keywords,
            is_fixture=False,
            search_trend_points=points,
            group_name=request.trend_name,
        )

    def _post(self, payload: Mapping[str, object], headers: Mapping[str, str]) -> httpx.Response:
        try:
            if self._client is not None:
                response = self._client.post(
                    f"{self._base_url}{NAVER_SEARCH_TREND_PATH}",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
            else:
                with httpx.Client() as client:
                    response = client.post(
                        f"{self._base_url}{NAVER_SEARCH_TREND_PATH}",
                        json=payload,
                        headers=headers,
                        timeout=self._timeout,
                    )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise NaverNetworkError("NAVER API HUB request failed") from exc

        if response.status_code in {401, 403}:
            raise NaverAuthenticationError("NAVER API HUB authentication failed")
        if response.status_code == 429:
            raise NaverRateLimitError("NAVER API HUB rate limit exceeded")
        if 400 <= response.status_code < 500:
            raise NaverValidationError("NAVER API HUB rejected the request")
        if response.status_code >= 500:
            raise NaverProviderError("NAVER API HUB provider error")
        return response

    def _parse_response(
        self, response: httpx.Response, request: CollectionRequest
    ) -> tuple[SearchTrendPoint, ...]:
        try:
            body = cast(dict[str, Any], response.json())
            results = body["results"]
            if not isinstance(results, list) or len(results) != 1:
                raise TypeError
            result = results[0]
            if not isinstance(result, dict) or not isinstance(result.get("data"), list):
                raise TypeError
            points = tuple(
                SearchTrendPoint(
                    period=datetime.strptime(item["period"], "%Y-%m-%d").date(),
                    ratio=Decimal(str(item["ratio"])),
                )
                for item in result["data"]
            )
        except (KeyError, TypeError, ValueError, InvalidOperation, httpx.DecodingError) as exc:
            raise NaverMalformedResponseError(
                "NAVER API HUB returned a malformed response"
            ) from exc
        if len({point.period for point in points}) != len(points):
            raise NaverMalformedResponseError("NAVER API HUB returned duplicate periods")
        if any(point.ratio < Decimal(0) or point.ratio > Decimal(100) for point in points):
            raise NaverMalformedResponseError("NAVER API HUB returned an invalid ratio")
        return points
