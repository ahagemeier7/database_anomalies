# Reliability and Model-Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose database outages, accurately label the bootstrap model as Isolation Forest-only, and make the front-end dependency build reproducible and safer.

**Architecture:** The backend maps a dedicated data-access exception to HTTP 503 at the API boundary. Initial training explicitly stores IF mode before registering the pipeline. The frontend uses the lockfile in Docker and excludes local build input.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, React/Vite, npm, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-27-reliability-and-model-mode-design.md`

## Global Constraints

- Do not expose database connection details to API clients.
- Keep hybrid retraining behavior unchanged.
- Use `npm ci` in Docker.
- Add a test before each behavior change.

---

### Task 1: Database outage responses

**Files:**
- Modify: `anomalies_hub_backend/crud/anomalies.py`
- Modify: `anomalies_hub_backend/api/anomalies.py`
- Create: `tests/test_anomalies_api.py`

- [ ] Write a failing API test that replaces the CRUD operation with `DatabaseUnavailableError` and expects HTTP 503 with `Database temporarily unavailable.`
- [ ] Run the test and confirm it fails because the exception type/handler does not exist.
- [ ] Add the exception, propagate SQLAlchemy failures from anomaly reads, and map it to HTTP 503 in the API route.
- [ ] Run the focused test, then the full pytest suite.

### Task 2: Bootstrap model mode

**Files:**
- Modify: `anomaly_detector/src/training_pipeline/workers/worker_models_initial.py`
- Create: `tests/test_initial_model_mode.py`

- [ ] Write a failing test asserting initial training registers the model with `inference_mode='if'` and updates `pipelines_config` accordingly.
- [ ] Run the test and confirm it fails against the current initial-training flow.
- [ ] Persist IF mode when initial training creates its version and pipeline configuration.
- [ ] Run the focused test and full pytest suite.

### Task 3: Reproducible Node build

**Files:**
- Modify: `anomalies_hub_frontend/anomalies_hub_frontend/Dockerfile`
- Create: `anomalies_hub_frontend/anomalies_hub_frontend/.dockerignore`
- Modify: `anomalies_hub_frontend/anomalies_hub_frontend/package.json`
- Modify: `anomalies_hub_frontend/anomalies_hub_frontend/package-lock.json`

- [ ] Run `npm audit` and record current production/development vulnerabilities.
- [ ] Replace Docker `npm install` with `npm ci` and exclude `node_modules`, `dist`, logs and local env files from build context.
- [ ] Update only dependency versions required by the audit, then run `npm audit`, lint and build.
- [ ] Build the front-end Docker image and validate Compose configuration.
