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

초기 Docker Compose 구성은 `api`, `scheduler`, `postgres`, 이후 `frontend`를 독립 service로 둘 수 있다. Phase 0의 빈 `docker-compose.yml`은 실행 구성을 가장하지 않기 위해 구현하지 않는다. Phase 1에서 DB와 API가 실제 health check를 통과하는 최소 구성부터 추가한다.

추가 provider는 collector 계약과 normalized record를 구현하고, schema 변화가 필요한 경우 migration 및 집계 contract test를 함께 제공한다.
