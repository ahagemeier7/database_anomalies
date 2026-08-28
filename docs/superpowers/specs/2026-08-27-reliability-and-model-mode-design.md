# Reliability and Model-Mode Design

## Goal

Make database outages visible to API clients, accurately represent the initial model as Isolation Forest-only, and make the front-end dependency install reproducible and smaller.

## Database failures

The anomaly CRUD layer must no longer turn database exceptions into successful empty responses. Each query operation raises a dedicated `DatabaseUnavailableError` that preserves the original cause. API routes translate that error to HTTP 503 with a stable, non-sensitive detail message. Unexpected programming errors remain HTTP 500.

## Initial model mode

Initial training has no reviewed labels, so it creates only an Isolation Forest. The initial model version and pipeline registration must persist `inference_mode = 'if'`; this causes the worker and dashboard to describe the actual active model. Hybrid mode remains available after retraining produces a Random Forest model from reviewed records.

## Node build

The front-end Docker build installs exactly the lockfile dependency tree with `npm ci`. A `.dockerignore` excludes local dependencies, build artifacts and editor files from Docker contexts. Dependency updates are limited to the lockfile/package manifest changes required by `npm audit` without breaking the production build.

## Verification

Add Python regression tests for API 503 behavior and initial training mode. Run the full pytest suite, front-end lint/audit/build, Compose configuration validation, and Docker front-end build.
