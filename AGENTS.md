# TrendSignal 개발 에이전트 지침

이 문서는 저장소 전체에 적용된다. 더 하위 디렉터리에 별도의 `AGENTS.md`가 생기면 해당 범위에서는 더 구체적인 지침을 우선한다.

## 프로젝트 목표

TrendSignal은 사용자가 등록한 Trend와 alias를 기준으로 YouTube 및 NAVER 검색 행동의 초기 신호를 수집하고, Day 1~3 데이터로 Day 7 성장과 `RISING` / `STABLE` / `FADING` 상태를 예측하는 연구·포트폴리오 프로젝트다. 특정 도메인에 종속되지 않는 비교 가능한 데이터 모델과 재현 가능한 실험을 우선한다.

## 현재 범위

- Phase 0은 저장소 골격과 연구·아키텍처·데이터·모델 계획 문서만 다룬다.
- 실제 외부 API 호출, 모델 학습, 프론트엔드 구현은 Phase 0 범위 밖이다.
- Version 1은 사용자가 Trend와 alias를 직접 등록한다. 자동 Trend discovery는 Version 2다.
- 범위가 불명확하면 가장 작은 수직 단위로 제한하고 문서의 결정 사항을 따른다.

## 디렉터리 책임

- `backend/`: FastAPI API, SQLAlchemy 모델, Alembic migration, 애플리케이션 서비스
- `pipeline/`: provider collector, 정규화, 일 단위 집계, 스케줄링
- `ml/`: feature 생성, dataset split, 학습, 평가, artifact metadata
- `notebooks/`: 탐색 및 연구용 노트북; 운영 로직의 유일한 구현 장소로 사용하지 않는다.
- `frontend/`: Next.js, TypeScript, Tailwind CSS, Recharts UI
- `docs/`: 연구 질문, 아키텍처, 데이터 계약, 모델·검증 계획

## 공통 개발 규칙

- Python에는 type hint를 사용하고, 공개 함수와 경계 계층에는 명확한 입출력 계약을 둔다.
- provider별 구현은 공통 interface 또는 추상 클래스 뒤에 둔다. 외부 응답을 내부 도메인 모델에 직접 노출하지 않는다.
- 모든 수집 데이터에 `source`와 UTC 기준 `collected_at`을 기록한다. 원본 provider 식별자를 보존한다.
- 누적 지표(조회수, 좋아요, 댓글)는 덮어쓰지 않고 snapshot으로 저장한다.
- 외부 API의 timeout, 재시도 가능한 오류, quota/rate limit, 부분 실패를 명시적으로 처리한다.
- secret과 실제 원본 데이터는 commit하지 않는다. 설정 키는 `.env.example`에 이름과 설명만 추가한다.
- fixture/mock 데이터는 코드, API 응답, 화면에서 실제 데이터와 혼동되지 않게 표시한다.
- 날짜·시간 저장은 UTC를 기본으로 하고, Trend의 `day_index` 산정 규칙은 데이터 정의 문서를 따른다.
- 새 의존성은 필요성과 라이선스를 확인하고 해당 패키지의 manifest/lockfile에 기록한다.

## 데이터 및 ML 안전 규칙

- feature 계산 시 예측 기준 시점 이후의 데이터는 절대 참조하지 않는다.
- 동일 Trend의 미래 관측치가 train에 들어간 상태로 과거를 평가하지 않는다.
- random row split을 기본 검증법으로 사용하지 않는다. 시간 순서와 `trend_id` 그룹을 함께 고려한다.
- target 정의와 label threshold는 실험 전에 versioning하며, 결과를 본 뒤 조정했다면 새 실험으로 기록한다.
- 학습 실행마다 feature 목록, target, train/validation/test 기간, Trend 목록 또는 split 규칙, metric, seed, 코드·데이터 버전, 모델 버전을 기록한다.
- 성능 수치를 임의 생성하지 않는다. 계산되지 않은 수치는 `N/A`, mock은 `MOCK`으로 표시한다.

## 테스트 및 완료 기준

- 변경 기능에는 정상 경로와 핵심 실패 경로 테스트를 추가한다.
- collector는 실제 API 대신 fixture/mock 기반 contract test가 가능해야 한다.
- 집계·feature·label 로직은 경계 날짜와 결측치 사례를 포함해 단위 테스트한다.
- DB schema 변경은 Alembic migration과 downgrade 가능성을 검토한다.
- 완료 전 관련 test, lint, type check를 실행하고 실행하지 못한 검증은 결과와 함께 밝힌다.
- 문서와 구현이 다르면 같은 변경에서 문서 또는 구현을 정합하게 갱신한다.

## 변경 원칙

- 작고 검토 가능한 변경을 선호한다.
- 사용자의 기존 변경과 관련 없는 파일을 되돌리거나 정리하지 않는다.
- 자동 discovery, 댓글 본문 저장, Day 14 모델, SHAP 같은 후속 범위는 명시적 요청 없이 앞당기지 않는다.
