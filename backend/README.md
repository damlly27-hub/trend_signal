# TrendSignal Backend

Phase 1-C adds the NAVER API HUB Search Trend provider behind the existing collector contract. Calls are manual only; there is no scheduler, daily aggregation, feature engineering, or forecasting. Tests use `httpx.MockTransport` and never call NAVER.

