# 시스템 아키텍처

## 1. 목표와 원칙

Version 1은 사용자가 등록한 Trend를 안정적으로 수집하고, 원본에 가까운 snapshot부터 일 집계·feature·prediction까지 추적 가능한 흐름을 제공한다.

- provider 교체/추가 가능성
- append-only snapshot과 재집계 가능성
- API, 수집, ML 책임 분리
- 모든 파생값의 lineage와 version
- quota·부분 실패에 견디는 idempotent job
- 실제 결과와 fixture/mock의 명시적 구분

## 2. 논리 구성

```text
[Next.js UI]
      |
      v
[FastAPI API] -----> [PostgreSQL]
      |                    ^
      | register/query     | snapshots, daily aggregates,
      v                    | runs, predictions, experiments
[Application Services]     |
                           |
[APScheduler] -> [Collection Orchestrator]
                       |         |
                       v         v
              [YouTube Adapter] [NAVER Adapter]
                       |         |
                       +-----> normalize/deduplicate
                                      |
                                      v
                                daily aggregation
                                      |
                                      v
                         feature/training/evaluation jobs
```

초기에는 scheduler를 별도 worker framework 없이 APScheduler로 시작한다. API 프로세스와 scheduler 프로세스는 논리적으로 분리해 중복 실행을 막고, 규모가 커지면 queue/worker로 교체할 수 있게 job interface를 유지한다.

## 3. 계층별 책임

### Backend

- Trend/alias 등록, 수정, 조회
- 집계 시계열, 최신 상태, prediction, experiment 결과 조회
- 입력 검증과 응답 schema
- transaction 경계 및 application service 호출
- 실제 데이터 여부와 freshness 노출

### Pipeline

- provider-neutral `Collector` 계약
- provider request 구성, pagination, timeout, retry, quota 처리
- 외부 응답을 내부 record로 정규화
- video ID 기준 deduplication과 snapshot append
- 일 집계 생성 및 재실행
- collection run 상태와 오류 기록

개념적 계약 예시는 다음과 같다. Phase 1에서 실제 Python protocol로 확정한다.

```python
class Collector(Protocol):
    provider: ProviderName

    def collect(self, request: CollectionRequest) -> CollectionResult: ...
```

`CollectionResult`는 성공 데이터뿐 아니라 요청 window, 수집 시각, pagination/quota 정보, 부분 실패를 포함한다.

### ML

- cutoff-aware feature dataset 생성
- target/label 생성과 definition version 적용
- leakage-safe split
- baseline 학습·평가·artifact metadata 저장
- inference 결과와 model version 연결

### Frontend

- Dashboard: 추적 Trend, freshness, score/status
- Detail: 일별 SNS·검색 지표와 Day 7 prediction
- Explanation: feature importance 및 추후 SHAP
- Comparison: 초기 곡선 정규화 비교
- Evaluation: 모델별 metric과 actual 비교

미학적 완성도 이전에 `MOCK`, `STALE`, `INSUFFICIENT_DATA`, prediction version을 명확히 표시한다.

## 4. 데이터 흐름

1. 사용자가 Trend와 alias를 등록한다.
2. scheduler가 due Trend/provider 조합에 대해 `collection_run`을 생성한다.
3. adapter가 외부 API를 호출하고 provider metadata를 포함한 normalized record를 반환한다.
4. pipeline이 원본 식별자 기준으로 entity를 upsert하고 metric snapshot은 append한다.
5. aggregator가 특정 UTC date의 Trend × Date row를 idempotent하게 계산한다.
6. feature job은 명시된 `as_of_date`까지만 읽어 dataset을 생성한다.
7. training/evaluation은 frozen split과 metadata를 저장한다.
8. inference 결과는 Trend, cutoff, model version과 함께 API/UI에 제공된다.

## 5. 저장소 모듈 경계(계획)

```text
backend/
  app/
    api/            # HTTP routes and schemas
    core/           # settings, logging
    db/             # session, ORM models, repositories
    services/       # use cases
  migrations/
  tests/
pipeline/
  collectors/       # interface + provider adapters
  normalization/
  aggregation/
  scheduling/
  tests/
ml/
  features/
  datasets/
  training/
  evaluation/
  tests/
frontend/
  src/
  tests/
```

Phase 0에서는 이 전체를 빈 파일로 미리 만들지 않는다. 각 Phase에서 필요한 최소 package부터 추가한다.

## 6. 데이터베이스 경계

예상 핵심 table은 다음과 같다.

- catalog: `trends`, `trend_aliases`
- provider entities: `youtube_videos`, `youtube_video_trends`
- time series: `youtube_video_snapshots`, `naver_search_observations`, `trend_daily_observations`
- operations: `collection_runs`, `collection_run_errors`
- ML: `feature_datasets`, `model_experiments`, `model_artifacts`, `predictions`

정확한 column과 key는 [데이터 정의](data-definition.md)에 기술한다. 대용량 raw response 전체 저장은 기본값이 아니며, 필요 시 보존 기간과 민감정보 검토 후 별도 storage를 설계한다.

## 7. 신뢰성 설계

- **Idempotency**: `provider + external_id` entity key, snapshot 자연키, aggregate upsert key를 둔다.
- **Retry**: timeout/5xx/429만 bounded exponential backoff와 jitter로 재시도한다.
- **Rate limit**: provider별 quota budget과 `retry_after`를 존중한다.
- **Partial failure**: 전체 run을 성공으로 위장하지 않고 `PARTIAL`과 오류 단위를 기록한다.
- **Observability**: run ID, provider, trend ID, latency, item count, quota cost를 structured log로 남긴다.
- **Freshness**: 마지막 성공 수집 시각과 데이터 coverage를 API에 노출한다.
- **Concurrency**: 동일 Trend/provider/window의 중복 job에 DB-level uniqueness 또는 lock을 적용한다.

## 8. 보안과 개인정보

- secret은 환경변수 또는 배포 secret store에서만 주입한다.
- 로그에 API key, authorization header, 댓글 작성자 식별자를 남기지 않는다.
- 댓글 본문 수집은 별도 feature flag로 기본 비활성화한다.
- 공개 API 이용약관, 보존/삭제 요구, 최소 수집 원칙을 provider별로 문서화한다.
- DB 계정은 서비스별 최소 권한을 사용하고 외부 공개 port는 개발 환경에 제한한다.

## 9. 배포 단위와 확장

초기 Docker Compose 구성은 Phase 1-A에서 `api`와 `postgres`만 제공한다. 두 service는 health check를 가지며 API 시작 전에 migration을 적용한다. `scheduler`와 `frontend`는 각 구현 Phase에서 독립 service로 추가한다.

추가 provider는 collector 계약과 normalized record를 구현하고, schema 변화가 필요한 경우 migration 및 집계 contract test를 함께 제공한다.

## 10. Phase 1-A 구현 결정

Trend catalog의 첫 수직 슬라이스는 Router → Schema → Service → Repository → ORM → Database Session 책임을 분리한다. Provider와 pipeline 의존성은 두지 않는다.

- `trends.name`은 database unique constraint로 중복을 막는다.
- alias는 Unicode NFKC, case folding, 연속 공백 축약 후 `(trend_id, normalized_alias)` unique constraint로 중복을 막는다.
- Trend 삭제 API는 제공하지 않는다. Alias FK는 `ON DELETE RESTRICT`로 두어 향후 연구 데이터가 연결된 Trend의 우발적 hard delete를 허용하지 않는다.
- API 테스트는 production URL을 사용하지 않고 test별 임시 SQLite database를 생성한다.

## 11. Phase 1-B 구현 결정

`CollectionRequest`와 `CollectionResult`는 provider adapter 밖의 내부 계약이며 `Collector` Protocol은 `collect(request) -> result`만 요구한다. Alias별 오류 목록과 `PARTIAL` 상태로 부분 실패를 표현하므로 향후 YouTube나 NAVER adapter가 같은 계약을 구현할 수 있다.

개발용 `FixtureCollector`는 외부 통신 없이 고정 값을 반환한다. 각 실행은 `collection_runs` 한 행과 `observations` 한 행을 새로 추가하며 기존 관측을 갱신하지 않는다. `observations`는 수집 당시의 provider-neutral 원시 관측 스냅샷이고, 향후 `trend_daily_observations`는 여러 원시 관측을 UTC 날짜 단위로 계산한 파생 데이터다.

Phase 1-A schema에는 alias 활성 필드가 없으므로 현재는 등록 alias 전체를 request에 포함한다. Provider별/활성 alias 정책은 해당 물리 필드가 추가되는 후속 migration에서 적용한다.

## 12. Phase 1-C NAVER Search Trend 결정

`NaverSearchTrendCollector`는 기존 `Collector`의 request/result 계약을 재사용하며 HTTP client를 주입할 수 있다. 기본 endpoint는 NAVER API HUB의 `/search-trend/v1/search`이고 timeout을 명시한다. Credential은 collector 사용 시점에만 검사하므로 credential이 없는 환경에서도 API 애플리케이션 자체는 시작된다.

Trend 하나를 keyword group 하나로 변환한다. canonical Trend name과 등록 alias를 순서 보존 방식으로 중복 제거하며, 공식 API 제한인 그룹당 20개를 넘으면 alias를 버리지 않고 validation error를 반환한다. 인증 헤더는 DB metadata, 오류 응답, 로그에 저장하지 않는다.

한 호출이 여러 period를 반환하므로 Phase 1-B의 단일 generic `observations` 행에 배열이나 임의 집계를 넣지 않는다. 실행 window와 keyword metadata는 `collection_runs`에, 각 period/ratio는 `search_trend_observations`에 저장한다. `(collection_run_id, period)`는 고유하지만 다른 run의 동일 period는 허용하여 window 변화에 따른 ratio 차이를 보존한다. Raw response 전체는 provider 형식 변화와 불필요한 저장 중복을 피하기 위해 보존하지 않고 재현에 필요한 request window, time unit, group name, keywords와 수집 시각만 보존한다.
