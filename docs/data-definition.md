# 데이터 정의

## 1. 목적과 표준

이 문서는 Version 1의 논리 데이터 계약을 정의한다. 물리 PostgreSQL schema와 SQLAlchemy 모델은 Phase 1에서 이 계약을 바탕으로 작성한다.

- 모든 내부 ID는 UUID 사용을 기본안으로 한다.
- 모든 timestamp는 timezone-aware UTC로 저장하고 이름에 `_at`을 사용한다.
- 일 단위 `date`는 UTC calendar date를 기본으로 한다.
- 모든 provider 관측에는 `source`, `collected_at`, 가능한 경우 `collection_run_id`를 둔다.
- count는 0 이상이다. API가 값을 제공하지 않은 경우 0이 아니라 `NULL`로 저장한다.
- enum, feature, target 규칙은 `definition_version`으로 추적한다.

## 2. 핵심 식별자와 enum

| 이름 | 값/형식 | 의미 |
|---|---|---|
| `trend_id` | UUID | 내부 Trend 식별자 |
| `source` | `YOUTUBE`, `NAVER_SEARCH_TREND` | 관측 provider |
| `category` | versioned slug | 예: `food`, `meme`, `game`, `beauty`, `product`, `challenge`, `other` |
| `trend_status` | `RISING`, `STABLE`, `FADING` | versioned label 결과 |
| `data_kind` | `REAL`, `FIXTURE`, `MOCK` | 데이터 출처의 진위 표시 |
| `run_status` | `PENDING`, `RUNNING`, `SUCCEEDED`, `PARTIAL`, `FAILED`, `RATE_LIMITED` | 수집 실행 상태 |

category는 자유 텍스트와 통제 vocabulary를 혼용하지 않는다. 변경 시 mapping version을 기록한다.

## 3. Catalog

### `trends`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `id` | UUID | Y | Trend ID |
| `name` | text | Y | 표시 이름 |
| `slug` | text | Y | 고유 URL/API slug |
| `category` | text/enum | Y | versioned category |
| `locale` | text | Y | 기본 시장/언어. 예: `ko-KR` |
| `observation_started_on` | date | N | Day 1 기준일 |
| `observation_start_reason` | text | N | 등록일/threshold 등 시작 근거 |
| `is_active` | boolean | Y | 수집 활성 여부 |
| `created_at`, `updated_at` | timestamptz | Y | 감사 timestamp |

### `trend_aliases`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `id` | UUID | Y | alias ID |
| `trend_id` | UUID FK | Y | 소속 Trend |
| `alias` | text | Y | 검색어 원문 |
| `normalized_alias` | text | Y | 중복 검사용 정규화 값 |
| `provider` | enum/null | N | null이면 공통, 값이 있으면 provider 전용 |
| `language` | text | N | BCP 47 언어 tag |
| `is_primary`, `is_active` | boolean | Y | 대표/활성 여부 |
| `created_at` | timestamptz | Y | 생성 시각 |

권장 제약: `(trend_id, normalized_alias, provider)` unique. alias normalization은 공백·Unicode·대소문자 규칙을 versioning한다.

## 4. YouTube 원천 및 snapshot

### `youtube_videos`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `video_id` | text PK | Y | YouTube video ID |
| `title` | text | Y | 수집 당시 최신 제목 |
| `published_at` | timestamptz | Y | 게시 시각 |
| `channel_id` | text | Y | creator 식별자 |
| `channel_name` | text | N | 표시 이름, 변경 가능 |
| `first_seen_at`, `last_seen_at` | timestamptz | Y | 관측 범위 |
| `source` | enum | Y | `YOUTUBE` |

### `youtube_video_trends`

Trend와 검색 결과 video의 다대다 관계를 보존한다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `trend_id` | UUID FK | Y | Trend |
| `video_id` | text FK | Y | video |
| `matched_alias_id` | UUID FK | N | 최초 또는 대표 match alias |
| `first_matched_at` | timestamptz | Y | 최초 발견 시각 |
| `match_method` | text | Y | query, manual 등 |

### `youtube_video_snapshots`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `id` | UUID | Y | snapshot ID |
| `video_id` | text FK | Y | video |
| `view_count` | bigint | N | 누적 조회수 |
| `like_count` | bigint | N | 누적 좋아요 수 |
| `comment_count` | bigint | N | 누적 댓글 수 |
| `collected_at` | timestamptz | Y | 실제 수집 시각 |
| `source` | enum | Y | `YOUTUBE` |
| `collection_run_id` | UUID FK | Y | 실행 lineage |
| `data_kind` | enum | Y | 실제/fixture/mock |

동일 영상의 metric은 update로 덮어쓰지 않는다. provider가 숨긴 값은 `NULL`이다. 권장 자연키는 `(video_id, collected_at, collection_run_id)`이며 재시도 idempotency key를 별도로 둘 수 있다.

댓글 본문은 Version 1 필수 schema가 아니다. 활성화할 경우 원문 최소화, author 식별자 비저장/가명화, 수집 근거와 삭제 정책을 별도 정의한다.

## 5. NAVER Search Trend 관측

### `naver_search_observations`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| `id` | UUID | Y | 관측 ID |
| `trend_id` | UUID FK | Y | Trend |
| `date` | date | Y | provider 결과 날짜 |
| `search_ratio` | numeric | Y | 요청 내 상대 관심도 |
| `keyword_group` | text | Y | 요청 keyword group ID/name |
| `query_window_start`, `query_window_end` | date | Y | ratio 정규화 범위 |
| `device`, `gender`, `ages` | jsonb/null | N | 선택 filter |
| `source` | enum | Y | `NAVER_SEARCH_TREND` |
| `collected_at` | timestamptz | Y | 수집 시각 |
| `collection_run_id` | UUID FK | Y | 실행 lineage |
| `data_kind` | enum | Y | 실제/fixture/mock |

`search_ratio`는 절대량이 아니며 동일 요청 window/group 안에서만 직접 비교 가능하다. window가 다른 series 병합에는 calibration/version 규칙이 필요하다.

## 6. Trend × Date 일 집계

### `trend_daily_observations`

| 필드 | 타입 | 필수 | 정의 |
|---|---|---:|---|
| `trend_id` | UUID FK | Y | Trend |
| `date` | date | Y | UTC 집계일 |
| `day_index` | integer | Y | `date - observation_started_on + 1` |
| `category` | text/enum | Y | 집계 당시 category |
| `youtube_video_count` | integer | N | 해당 일 cutoff까지 발견된 관련 영상 수 |
| `youtube_new_video_count` | integer | N | 해당 일 최초 발견 또는 게시 기준 신규 영상 수; 선택 규칙 versioning |
| `youtube_unique_creator_count` | integer | N | 관련 영상의 distinct `channel_id` 수 |
| `youtube_total_views` | bigint | N | 영상별 해당 일 마지막 snapshot 조회수 합 |
| `youtube_total_comments` | bigint | N | 영상별 해당 일 마지막 snapshot 댓글 수 합 |
| `youtube_total_likes` | bigint | N | 영상별 해당 일 마지막 snapshot 좋아요 수 합 |
| `naver_search_ratio` | numeric | N | 비교 가능한 series의 해당 일 ratio |
| `coverage` | jsonb | Y | provider별 성공/결측/부분 수집 상태 |
| `source_lineage` | jsonb | Y | 사용 run/snapshot/window 참조 |
| `aggregation_version` | text | Y | 집계 코드/정의 version |
| `computed_at` | timestamptz | Y | 계산 시각 |
| `data_kind` | enum | Y | 입력 lineage에 따른 값 |

Primary/unique key는 `(trend_id, date, aggregation_version)`을 기본안으로 한다. 여러 alias에 매칭된 동일 영상은 한 번만 집계한다. `youtube_new_video_count`의 게시일 기준과 최초발견일 기준 값은 의미가 다르므로 구현 전에 하나를 primary로 고정하거나 두 필드로 분리한다.

## 7. 파생 feature 정의 후보

아래는 계획이며 수식은 `feature_definition_version`에서 고정한다.

| Feature | 후보 정의 | 주의점 |
|---|---|---|
| `view_growth_rate` | `(views_t - views_t-1) / max(views_t-1, ε)` | 작은 분모, 음수 correction |
| `comment_growth_rate` | 댓글 누적값의 일 성장률 | 숨김/비활성 댓글 |
| `video_growth_rate` | 관련 영상 수 또는 신규 영상 수 성장률 | 발견일과 게시일 구분 |
| `creator_growth_rate` | unique creator 수 성장률 | channel ID 결측 |
| `search_growth_rate` | 비교 가능한 ratio의 변화율 | 요청 window 일관성 |
| `view_acceleration` | 성장량 또는 성장률의 2차 차분 | 3일 창의 높은 분산 |
| `comment_acceleration` | 댓글 변화의 2차 차분 | 결측 처리 |
| `unique_creator_ratio` | unique creators / video count | 0 분모 |
| lag feature | `x_t-1`, `x_t-2` | cutoff 이후 참조 금지 |
| rolling feature | 과거-only mean/std/slope | centered window 금지 |

결측치는 provider 미지원, 수집 실패, 실제 0을 구분하는 indicator와 함께 처리한다. 전체 데이터로 imputer/scaler를 fit하지 않고 train fold에만 fit한다.

## 8. Target과 label

### Regression target

Day 1~3 feature로 Day 7의 미래 성장 정도를 예측한다. 1차 후보는 log 안정화를 적용한 조회수 성장이다.

```text
target_day7_view_growth = log1p(total_views_day7) - log1p(total_views_day3)
```

대안으로 상대 성장률과 video/search 복합 target을 비교할 수 있으나, 하나의 실험에서 target을 혼합하지 않는다. `target_definition_version`과 Day 3/7 coverage 요건을 기록한다.

### Classification label

`RISING` / `STABLE` / `FADING`은 Day 3→7의 성장 target과 지속성 보조 조건으로 결정한다. 초기 threshold 후보는 train 기간의 분위수를 이용하되 다음 규칙을 지킨다.

- threshold는 train fold에서만 산출하고 validation/test에 적용한다.
- class 의미와 threshold를 model metadata에 저장한다.
- category별 threshold 사용 여부를 사전에 정하고 전체 threshold 결과와 분리 보고한다.
- 데이터가 부족하거나 coverage가 불충분하면 강제 label 대신 `UNLABELED` 처리한다.

## 9. 운영 및 ML metadata

### `collection_runs` 최소 필드

`id`, `provider`, `trend_id`, `requested_at`, `started_at`, `finished_at`, `status`, `query_window`, `item_count`, `quota_cost`, `attempt_count`, `error_code`, `error_summary`.

### `model_experiments` 최소 필드

`experiment_id`, `model_name`, `model_version`, `task_type`, `feature_list`, `feature_definition_version`, `target_definition_version`, `dataset_version`, `train_period`, `validation_period`, `test_period`, `split_strategy`, `hyperparameters`, `seed`, `metrics`, `code_revision`, `created_at`.

### `predictions` 최소 필드

`id`, `trend_id`, `as_of_date`, `horizon_day`, `task_type`, `prediction_value` 또는 `predicted_class`, `model_version`, `feature_dataset_id`, `data_kind`, `created_at`. 실제값이 도착하면 별도 evaluation record에서 연결하며 prediction을 덮어쓰지 않는다.

## 10. 데이터 품질 규칙

- count 감소는 provider correction 가능성이 있으므로 삭제하지 않고 anomaly flag를 남긴다.
- 미래 `published_at`, 중복 external ID, 음수 count는 quarantine한다.
- Day 1~3 중 required provider coverage가 기준 미만이면 prediction 대상에서 제외하거나 낮은 신뢰도로 표시한다.
- aggregate는 source snapshot까지 역추적 가능해야 한다.
- fixture는 실제 provider namespace와 충돌하지 않는 ID prefix/전용 dataset을 사용한다.

## 11. Phase 1-A 물리 schema 범위

장기 논리 계약의 모든 필드를 최초 migration에 선반영하지 않는다. Phase 1-A의 물리 `trends` table은 `id`, `name`, `category`, `description`, `status`, `created_at`, `updated_at`만 포함한다. `slug`, `locale`, 관측 시작 정보는 해당 use case가 구현될 때 별도 migration으로 추가한다.

물리 `trend_aliases` table은 `id`, `trend_id`, `alias`, `normalized_alias`, `created_at`을 포함한다. provider/language/primary/active 필드는 provider별 alias 정책이 확정되는 후속 단계로 미룬다. `normalized_alias`는 API에 노출하지 않는 중복 방지용 내부 값이다.

이 단계의 `status`는 catalog lifecycle인 `ACTIVE`, `PAUSED`, `ARCHIVED`이며, ML 결과 label인 `RISING`, `STABLE`, `FADING`과 다른 개념이다.

## 12. Phase 1-B 물리 schema 범위

`collection_runs`는 `id`, `trend_id`, `provider`, `requested_at`, `collected_at`, `status`, `error_summary`, `is_fixture`, `created_at`을 저장한다. 각 `observations.collection_run_id`가 이 실행을 참조하여 lineage를 보존한다.

`observations`는 수집 시점의 provider-neutral 원시 관측값이다. `trend_id`, `source`, `collected_at`, count/ratio 값, `is_fixture`, `created_at`을 저장하며 동일 Trend의 반복 수집은 별도 행으로 append한다. 값이 제공되지 않으면 0 대신 `NULL`이다. Fixture 실행은 `source=FIXTURE`, `is_fixture=true`로 실제 데이터와 구분한다.

이 raw observation은 향후 UTC 날짜별 규칙으로 계산할 `trend_daily_observations`와 다르다. 일 집계는 raw 행을 덮어쓰거나 대체하지 않으며, 집계 version과 source lineage를 별도로 가져야 한다.

## 13. Phase 1-C NAVER Search Trend 물리 schema

`collection_runs`에 nullable `request_start_date`, `request_end_date`, `time_unit`, `group_name`, `keywords`를 추가한다. Fixture와 향후 다른 provider run에는 필요하지 않을 수 있으므로 nullable이며, NAVER Search Trend 성공 run에서는 모두 채운다. 인증 정보는 저장하지 않는다.

`search_trend_observations`는 `id`, `trend_id`, `collection_run_id`, `provider`, `period`, `ratio numeric(10,5)`, `collected_at`, `is_fixture`, `created_at`을 가진다. `(collection_run_id, period)`만 unique이므로 같은 period라도 서로 다른 collection run이면 별도 행으로 append된다.

NAVER ratio는 실제 검색 횟수가 아니다. 한 응답의 구간별 결과 중 최대값을 100으로 정규화한 상대 관심도이며 request window와 keyword group이 바뀌면 동일 period의 ratio도 달라질 수 있다. 따라서 서로 다른 run의 ratio를 절대 검색량처럼 직접 비교하지 않고, 비교 가능한 window/group인지 lineage를 먼저 확인한다. 이 원시 period 관측은 향후 daily metric이나 ML feature가 아니며 파생 단계에서 별도 version과 lineage를 가져야 한다.
