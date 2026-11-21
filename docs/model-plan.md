# 모델 계획

## 1. 목표

Version 1은 Day 1~3 관측으로 두 작업을 수행한다.

1. **Regression**: Day 3 이후 Day 7까지의 성장 정도 예측
2. **Classification**: Day 7 결과를 `RISING` / `STABLE` / `FADING`으로 분류

Day 14, deep learning, 자동 Trend discovery, 본격적인 SHAP 설명은 후속 범위다. 데이터 수가 작을 때 복잡한 모델을 성공 조건으로 삼지 않는다.

## 2. Dataset contract

한 학습 sample은 하나의 Trend와 하나의 `as_of_day=3` cutoff를 가진다. feature 계산은 해당 Trend의 Day 1~3에서만 수행하고, target은 Day 7 종료 후 생성한다.

필수 sample metadata:

- `trend_id`, category, locale
- `observation_started_on`, `feature_cutoff_date`, `target_date`
- feature/target/aggregation definition version
- provider coverage와 결측 indicator
- data kind 및 dataset version

동일 Trend에서 여러 rolling sample을 만들 경우 인접 sample이 서로 다른 fold에 흩어지지 않도록 group 정책을 적용한다.

## 3. Feature set

### 규모(level)

- Day 1/2/3의 total views, comments, likes
- video count, new video count, unique creator count
- NAVER search ratio

긴 꼬리 분포에는 `log1p` 변환 후보를 둔다.

### 성장과 속도

- view/comment/video/creator/search growth rate
- Day 1→2, Day 2→3 absolute delta
- 3일 slope 및 가능한 acceleration
- 신규 영상 생산 속도

### 확산 구조와 engagement

- unique creator ratio
- comments/views, likes/views (안전한 분모와 결측 indicator)
- creator 집중도는 channel별 데이터가 충분할 때 추가
- YouTube와 검색 신호의 방향 일치 여부

### Context

- category, locale, 시작 weekday
- provider coverage와 collection lag

Trend 이름이나 alias 원문은 baseline feature에서 제외해 암기와 sparse leakage를 줄인다.

## 4. Target 및 label

1차 regression target 후보는 다음과 같다.

```text
y_reg = log1p(youtube_total_views_day7) - log1p(youtube_total_views_day3)
```

Day 7 총 조회수가 unavailable하면 sample을 임의로 0 처리하지 않는다. 검색 또는 복합 성장 target은 별도 experiment로 둔다.

classification threshold는 regression target의 train-fold 분포를 기준으로 사전 정의한다. 예를 들어 하위/상위 분위수로 세 class를 나누는 방식은 가능하지만, 정확한 분위수는 class balance와 의미 해석을 exploratory 단계에서 정한 뒤 versioning한다. test 정보를 사용해 threshold를 재조정하지 않는다.

## 5. Baseline과 모델 순서

| 순서 | 모델 | 목적 |
|---:|---|---|
| 0 | Naive | 복잡한 모델이 넘어야 할 기준선 |
| 1 | Linear Regression / Logistic Regression | 방향성과 단순 결합 효과 확인 |
| 2 | Random Forest | 비선형성과 interaction 확인 |
| 3 | XGBoost | 충분한 표본에서 boosting 비교 |
| 4 | LightGBM | 충분한 표본에서 효율·성능 비교 |

Regression naive 후보는 train target 중앙값과 Day 1→3 성장 추세 외삽이다. Classification naive는 train majority class와 단순 성장 threshold rule을 모두 보고한다.

모든 preprocessing은 scikit-learn `Pipeline` 또는 동등한 fold-local 구조에 포함한다. hyperparameter 탐색은 training/validation 범위 안에서만 수행하며 test set은 최종 1회 평가에 보존한다.

## 6. Leakage-safe validation

random row split은 사용하지 않는다. 다음의 이중 제약을 만족한다.

1. **시간 제약**: validation/test Trend의 target 시점보다 뒤의 관측이나 label 정보가 train feature/target에 들어가지 않는다.
2. **Trend 그룹 제약**: 동일 `trend_id`의 sample이 train과 평가 fold에 동시에 존재하지 않는다.

권장 1차 전략은 **purged group temporal holdout**이다.

```text
Train:      시작/target 시점이 가장 이른 Trend 그룹
Purge gap:  최소 prediction horizon(또는 데이터 중첩을 막는 기간)
Validation: 그 다음 시기의 신규 Trend 그룹
Test:       가장 최근 시기의 신규 Trend 그룹
```

Trend가 동시에 여러 category에 걸치거나 시작일이 겹치는 경우, Trend의 최초 관측일을 group 정렬 기준으로 사용한다. 시간 경계에 걸친 Trend는 통째로 한 fold에 배정한다. 표본 수가 충분하면 expanding-window temporal group folds로 안정성을 평가한다.

추가 일반화 시험:

- category별 holdout 또는 leave-one-category-out
- 시작 규모별 slice
- 수집 coverage가 높은 sample만 사용한 sensitivity analysis

split manifest에는 각 fold의 기간, trend ID hash/list, sample 수, category 분포를 저장한다.

## 7. 평가 metric

### Regression

- Primary: MAE
- Secondary: RMSE
- 보조: median absolute error, Spearman rank correlation (우선순위 품질)

### Classification

- Primary: macro F1
- Secondary: class별 precision/recall/F1, weighted F1
- confusion matrix와 class support

평균 metric만 보고하지 않고 fold 및 category slice별 결과를 함께 제시한다. 모델 비교는 동일 dataset version과 split manifest에서 수행한다. 실용적으로 의미 있는 최소 개선 기준은 baseline 분산을 확인한 후 사전 등록한다.

## 8. 비교 및 ablation

RQ별 최소 비교:

- RQ1: naive vs 각 학습 모델
- RQ2: permutation importance + feature group ablation
- RQ3: YouTube-only vs YouTube+NAVER (동일 sample subset)
- RQ4: pooled model의 category slice 및 category holdout
- RQ5: 유사 Day 1~3 pair의 feature 차이와 오류 사례

NAVER 결측으로 결합 모델의 sample 수가 줄면 SNS-only 모델도 동일 subset에서 재평가해 공정하게 비교한다.

## 9. 설명 가능성과 오류 분석

Phase 1 baseline에서는 coefficient, permutation importance, partial dependence 가능성을 우선한다. tree 모델과 안정적인 평가 기반이 마련된 후 SHAP을 추가한다.

설명 화면과 보고서에는 다음을 구분한다.

- global model importance
- 개별 prediction에 대한 local contribution
- 상관/설명과 인과의 차이
- coverage와 out-of-distribution 경고

오류 분석은 큰 overprediction/underprediction, category, 초기 규모, 결측 패턴, spike형/지속형을 기준으로 수행한다.

## 10. 실험 추적과 재현성

각 run은 다음을 저장한다.

- model name/version, task type, code revision
- dataset/aggregation/feature/target definition version
- feature list와 preprocessing
- split manifest와 기간
- hyperparameter와 random seed
- 전체/fold/slice metric
- artifact URI와 checksum
- training 시작/종료 시각 및 환경 정보

모델 artifact만 저장하고 생성 경로를 잃지 않도록 한다. serialization 호환성과 dependency version을 함께 기록한다.

## 11. 단계별 진입 조건

- **Naive/linear 진입**: target이 확정되고 최소 coverage·split 검증 test가 통과
- **Random Forest 진입**: category/class별 표본 수와 baseline 오류 분석 확보
- **Boosting 진입**: temporal validation이 안정적이고 tuning을 감당할 표본 확보
- **SHAP 진입**: 최종 후보 모델이 고정되고 explanation 검증 계획 수립
- **배포 inference 진입**: 학습-서빙 feature parity, version 조회, insufficient-data 처리 test 통과
