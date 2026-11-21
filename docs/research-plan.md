# 연구 계획

## 1. 연구 목적

TrendSignal은 특정 분야의 인기 순위가 아니라, 사용자가 등록한 cross-domain Trend 후보의 초기 확산 신호로 미래 성장을 예측할 수 있는지를 검증한다. Version 1의 관측 창은 Day 1~3, 1차 예측 시점은 Day 7이다.

분석 단위는 `Trend × Date`이며 YouTube의 콘텐츠 생산·반응 신호와 NAVER의 검색 행동 신호를 결합한다. 연구 결과는 실제 관측과 재현 가능한 실험에만 근거하며, 개발 fixture의 결과를 연구 결과로 보고하지 않는다.

## 2. 연구 질문과 검증 가설

| ID | 연구 질문 | 검증 가능한 가설 | 주요 비교 |
|---|---|---|---|
| RQ1 | Day 1~3만으로 Day 7 성장을 예측할 수 있는가? | 학습 모델이 train-only naive baseline보다 낮은 out-of-time MAE를 보인다. | naive vs 학습 모델 |
| RQ2 | 어떤 early signal이 중요한가? | creator/video/search 확산 신호 중 일부가 단순 누적 조회수보다 안정적인 추가 설명력을 갖는다. | feature ablation, permutation importance |
| RQ3 | 검색 행동 결합이 유효한가? | YouTube+NAVER 모델이 동일 split의 YouTube-only 모델보다 성능이 좋다. | paired metric comparison |
| RQ4 | 도메인 공통 신호가 있는가? | 전체 모델이 unseen category 또는 category별 holdout에서도 naive baseline을 상회한다. | category slice/holdout |
| RQ5 | 초기 유사 Trend의 성공/실패 차이는 무엇인가? | Day 1~3 규모가 유사해도 creator 다양성·가속도·검색 동조성에서 차이가 관찰된다. | matched-pair 분석 |

가설은 방향을 제시할 뿐 결과를 미리 확정하지 않는다. 유의미한 개선이 없거나 category별 결과가 상충하는 것도 정식 결과로 기록한다.

## 3. 범위와 연구 모집단

### 포함

- 음식, 제품, 게임, 밈, 뷰티, 챌린지 등 복수 category
- 사용자가 사전에 등록한 Trend와 alias
- 공개 API로 합법적으로 접근 가능한 집계·metadata
- 최초 관측 이후 최소 7일의 관측이 확보된 Trend

### 제외 또는 후속 연구

- 자동 후보 발견과 유행어 mining
- 비공개 데이터와 개인 식별자 분석
- Day 14 target, 댓글 NLP, 인과 효과 추정
- provider가 제공하지 않는 절대 검색량의 추정

## 4. 핵심 정의

- **Day 1**: 해당 Trend가 시스템에 등록된 날짜가 아니라, 사전 정의한 관측 시작 조건을 최초 충족한 UTC 일자. 초기 연구에서는 수집 시작일을 사용하되 `observation_start_reason`을 기록한다.
- **Observation window**: Day 1 종료부터 Day 3 종료까지 사용 가능한 snapshot/일 집계.
- **Prediction horizon**: Day 7 종료 시점.
- **Future growth**: Day 3의 누적값 대비 Day 7 누적값의 변화. 0 분모 문제를 피하기 위해 최종 수식은 데이터 탐색 후 versioning한다.
- **Sustained trend**: 단일 spike가 아니라 정해진 기간 동안 생산·반응·검색 신호가 유지되는 상태. Version 1 label 규칙은 사전 등록된 threshold 설정으로 재현한다.

Day 1 정의와 target 수식은 결과를 보기 전에 고정하고 `definition_version`으로 기록한다.

## 5. 데이터 수집 설계

1. Trend와 category, alias, locale을 등록한다.
2. 동일 schedule에서 provider query를 수행하고 요청·응답 상태를 수집 실행 이력에 남긴다.
3. YouTube video metadata와 누적 지표를 snapshot으로 append한다.
4. NAVER relative search interest를 원본 구간·그룹과 함께 저장한다.
5. alias 중복 결과를 provider ID 기준으로 deduplicate한다.
6. UTC 날짜 기준으로 Trend × Date 집계를 생성하고 coverage/quality flag를 붙인다.

검색 ratio는 요청 구간과 keyword group에 따라 상대값이 달라질 수 있으므로 서로 다른 요청의 ratio를 무조건 이어 붙이지 않는다. 비교 가능한 고정 query window 또는 overlap calibration 전략을 실험 전에 정한다.

## 6. 실험 설계

### Baseline 순서

1. train 중앙값 또는 직전 성장 지속을 사용하는 naive baseline
2. Linear Regression
3. Random Forest
4. XGBoost
5. LightGBM

복잡한 모델은 단순 모델과 동일한 frozen split에서만 비교한다. 데이터 크기가 충분하지 않으면 tree boosting을 보류한다.

### 주요 실험군

- YouTube-only
- NAVER-only (보조 분석)
- YouTube + NAVER
- 규모 feature only vs 성장/가속도 포함
- creator feature 제거, search feature 제거 등 ablation

### 평가

- Regression: MAE를 1차 metric, RMSE를 2차 metric으로 사용
- Classification: macro F1을 1차 metric으로 하고 class별 precision/recall 및 confusion matrix 보고
- category별, 관측 coverage별, Trend 규모별 slice 결과 보고
- 가능하면 temporal fold별 metric의 평균뿐 아니라 분산/범위도 보고

검증 split의 세부 전략은 [모델 계획](model-plan.md)에 정의한다.

## 7. RQ5 matched-pair 분석

Day 3까지의 누적 조회수와 성장률이 유사한 Trend를 category와 시작 시기를 고려해 매칭한다. Day 7 결과가 성공/실패로 나뉜 pair에서 다음 차이를 탐색한다.

- unique creator 수와 creator concentration
- 신규 영상 생산 속도
- 댓글/조회 비율과 변화
- 검색 증가의 선행·동행·후행 관계
- 가속도와 초기 peak 이후 감속

이는 설명적·탐색적 분석이며 인과관계로 표현하지 않는다.

## 8. 편향, 한계, 윤리

- 사용자가 후보를 등록하므로 selection bias가 존재한다.
- API 검색 결과와 quota는 전체 플랫폼 활동을 완전히 대표하지 않는다.
- NAVER ratio는 절대 검색량이 아니며 query 구성에 민감하다.
- category와 alias 품질, 언어·지역 차이가 confounder가 될 수 있다.
- 삭제·비공개 전환 영상과 수집 실패는 missing-not-at-random일 수 있다.
- 댓글 본문 수집은 기본 비활성화하고, 필요 시 최소 범위·보존 기간·개인정보 제거 방침을 별도 승인한다.

## 9. 재현성 및 결과물

각 실험은 다음을 기록한다.

- 데이터 cutoff와 dataset/definition version
- Trend 모집 기준과 제외 사유
- feature/target 목록 및 계산 버전
- split 전략, 기간, seed
- 모델과 hyperparameter
- 전체 및 slice metric
- 코드 revision과 실행 환경
- 실패 실험과 알려진 한계

최종 연구 산출물은 데이터 카드, 실험표, 오류 분석, matched-pair 사례 분석으로 구성한다.
