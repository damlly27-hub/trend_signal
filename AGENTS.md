
# TrendSignal Repository Instructions

## Project Goal

TrendSignal is a research-oriented Early Trend Forecasting Platform.

The project collects early social-media and search behavior signals for manually registered trend topics and predicts future growth and persistence.

This repository must prioritize research reproducibility and data integrity over visual demos.

## Core Rules

Never fabricate real-world trend data.

Mock or fixture data must always be clearly labeled.

Never commit API keys, credentials, tokens, private datasets, or `.env` files.

All external observations must preserve their source and collection timestamp.

Do not overwrite historical metric values. Time-varying values such as YouTube view counts must be stored as snapshots.

Avoid data leakage. Future observations must never be used as features for earlier predictions.

Do not use ordinary random train/test splitting when it violates chronological ordering.

Keep model training reproducible by recording:

- feature set
- target definition
- dataset version
- training period
- test period
- model parameters
- evaluation metrics
- model version

## Architecture

Frontend:
Next.js + TypeScript

Backend:
FastAPI

Database:
PostgreSQL + SQLAlchemy + Alembic

ML:
pandas + scikit-learn + XGBoost + LightGBM + SHAP

Scheduling:
APScheduler

Testing:
pytest

Infrastructure:
Docker Compose

## Repository Responsibilities

`backend/`
Web API and application services.

`pipeline/`
External collectors, preprocessing, scheduled collection, and feature-generation logic.

`ml/`
Training, evaluation, inference, and model artifacts.

`notebooks/`
Exploratory analysis only. Production logic should eventually move into testable Python modules.

`frontend/`
Figma-based web implementation.

`docs/`
Research definitions, architecture decisions, feature definitions, model plans, and experiment documentation.

## API Integration

External providers must be isolated behind provider-specific modules.

Do not couple business logic directly to YouTube or NAVER APIs.

Collectors must handle:

- timeout
- unavailable data
- rate limits
- retries
- duplicate observations

## Coding Standards

Use Python type hints.

Use Pydantic schemas for API boundaries.

Use Alembic migrations for database schema changes.

Avoid large functions.

Keep collectors, feature engineering, model training, and web API responsibilities separated.

Add tests for non-trivial data transformation and forecasting logic.

Before implementing a major feature, read the relevant files in `docs/`.

For large changes, first explain which modules will change and why.

After a change, run relevant tests and summarize what changed.

## Research Integrity

This is not a demo that claims to predict trends without evidence.

Prediction results displayed in the frontend must indicate:

- prediction timestamp
- observation window
- forecast horizon
- model version
- predicted value
- actual value when available

Actual outcomes must be recorded separately from predictions so predictions cannot be retroactively modified after the result is known.