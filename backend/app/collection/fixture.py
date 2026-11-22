from datetime import UTC, datetime

from app.collection.contracts import (
    CollectionRequest,
    CollectionResult,
    CollectionStatus,
    ObservationData,
    ProviderName,
)


class FixtureCollector:
    """Deterministic fake collector for development and contract tests only."""

    provider = ProviderName.FIXTURE
    _observation = ObservationData(
        video_count=25,
        new_video_count=8,
        unique_creator_count=17,
        total_views=125_000,
        total_comments=1_800,
        total_likes=9_200,
        search_ratio=18.5,
    )

    def collect(self, request: CollectionRequest) -> CollectionResult:
        if request.provider is not self.provider:
            return CollectionResult(
                provider=self.provider,
                trend_id=request.trend_id,
                collected_at=datetime.now(UTC),
                observation=None,
                status=CollectionStatus.FAILED,
                used_aliases=(),
                warnings=(f"Unsupported provider requested: {request.provider}",),
                is_fixture=True,
            )
        return CollectionResult(
            provider=self.provider,
            trend_id=request.trend_id,
            collected_at=datetime.now(UTC),
            observation=self._observation,
            status=CollectionStatus.SUCCEEDED,
            used_aliases=request.aliases,
            warnings=("FIXTURE DATA: values are deterministic and are not real provider data",),
            is_fixture=True,
        )

