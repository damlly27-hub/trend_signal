# TrendSignal

초기 SNS 반응과 검색 행동을 결합해 앞으로 성장하고 지속될 Trend를 예측하는 cross-domain 연구·포트폴리오 프로젝트입니다.

TrendSignal은 이미 인기 있는 콘텐츠의 순위를 보여주는 서비스가 아닙니다. 사용자가 Trend와 관련 검색어(alias)를 등록하면, 초기 Day 1~3의 YouTube 및 NAVER Search Trend 신호를 일 단위로 수집·정규화하고 Day 7의 성장 정도와 상태를 예측하는 것을 목표로 합니다. 음식, 밈, 게임, 뷰티, 제품, 챌린지 등 서로 다른 분야에 공통적인 early signal이 있는지를 검증합니다.

> 현재 상태: **Phase 0 — 설계 및 저장소 골격**  
> 외부 API 호출, 실제 모델 학습, 프론트엔드 화면은 아직 구현하지 않았습니다. 성능 수치와 예측 결과도 생성하지 않았습니다.

## Version 1 범위

- 사용자가 Trend 이름, category, alias를 직접 등록
- YouTube Data API와 NAVER API HUB Search Trend를 provider로 지원
- 영상 지표를 snapshot으로 보존하고 Trend × Date 일 단위 시계열로 집계
- Day 1~3 feature로 Day 7 성장값을 예측하는 regression
- Trend를 `RISING` / `STABLE` / `FADING`으로 분류하는 classification
- 시간과 `trend_id`를 함께 고려한 leakage-safe validation
- Dashboard, Trend Detail, Explanation, Comparison, Model Evaluation 화면 설계

자동 Trend discovery, Day 14 예측, 댓글 본문 분석, Google Trends 및 추가 SNS, SHAP 기반 설명은 후속 범위입니다.

## 핵심 연구 질문

1. Day 1~3의 반응만으로 Day 7 성장을 예측할 수 있는가?
2. 조회수·댓글·영상·creator·검색량 성장 중 어떤 신호가 가장 유효한가?
3. SNS와 검색 행동을 결합하면 SNS 단독 모델보다 성능이 개선되는가?
4. 서로 다른 category에도 공통 early signal이 존재하는가?
5. 초기 곡선이 비슷하지만 이후 성공과 실패로 갈리는 Trend의 차이는 무엇인가?

자세한 가설과 실험 설계는 [연구 계획](docs/research-plan.md), 시스템 경계는 [아키텍처](docs/architecture.md), 필드 계약은 [데이터 정의](docs/data-definition.md), 모델·검증 전략은 [모델 계획](docs/model-plan.md)을 참고하세요.

## 저장소 구조

```text
.
├── AGENTS.md              # 저장소 전체 개발 원칙
├── README.md
├── docs/                  # 연구·아키텍처·데이터·모델 명세
├── backend/               # FastAPI, DB, migration (Phase 1+)
├── pipeline/              # collector, 정규화, 집계, scheduler (Phase 1+)
├── ml/                    # feature, training, evaluation (후속 Phase)
├── notebooks/             # EDA 및 연구 노트북 (후속 Phase)
└── frontend/              # Next.js UI (후속 Phase)
```

## 개발 로드맵

### Phase 0 — Foundation (현재)

- 요구사항과 연구 질문 명문화
- 저장소 골격 및 개발 원칙 작성
- 데이터 계약, 시스템 경계, 모델·검증 계획 수립
- secret 및 생성 데이터 제외 규칙 정의

### Phase 1 — 최소 데이터 기반

- Python backend/pipeline 패키지와 품질 도구 설정
- PostgreSQL 연결 및 최소 schema migration
- Trend·alias 등록/조회 API
- provider interface와 fixture 기반 collector contract test

### Phase 2 — 수집과 일 단위 집계

- YouTube 및 NAVER 실제 adapter 구현
- snapshot, retry/rate-limit 처리, 수집 실행 이력
- Trend × Date 집계와 scheduler

### Phase 3 — Baseline ML

- feature/target 생성과 leakage 검증
- naive, Linear Regression, Random Forest 비교
- classification baseline 및 실험 metadata 저장
- 이후 XGBoost, LightGBM, SHAP 확장

### Phase 4 — 제품 화면

- Dashboard와 Trend Detail부터 구현
- Comparison, Explanation, Model Evaluation 순차 구현
- 실제 데이터와 fixture/mock의 UI 구분

### Version 2

- 자동 Trend candidate discovery와 후보 품질 평가
- Day 14 및 추가 provider·도메인 확장

## 로컬 설정 원칙

아직 실행 가능한 서비스는 없습니다. Phase 1부터 `.env.example`을 복사한 로컬 `.env`에 실제 값을 넣어 사용합니다. `.env`, API key, database dump, 수집 원본, 모델 artifact는 commit하지 않습니다.

## 문서 상태

Phase 0의 정의는 설계 기준선이며, 실제 API 제약과 exploratory analysis 결과에 따라 변경될 수 있습니다. 변경 시 관련 문서와 schema/model version을 함께 갱신합니다.
