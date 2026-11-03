import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "anomalies_hub_backend"))
sys.path.insert(0, str(ROOT / "anomaly_detector"))
from anomalies_hub_backend import main
from api import pipeline as pipeline_api, anomalies as anomalies_api
from crud import pipeline


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE pipelines_config (target_table TEXT PRIMARY KEY, inference_mode TEXT, active_model_version TEXT, columns_to_ignore TEXT)"))
        conn.execute(text("INSERT INTO pipelines_config VALUES ('transactions','if','v001','id,Class')"))
        conn.execute(text("CREATE TABLE model_versions (target_table TEXT, version TEXT, translator_path TEXT, if_model_path TEXT, scaler_path TEXT, rf_model_path TEXT, metrics JSON, is_active BOOLEAN, created_at TEXT, UNIQUE(target_table, version))"))
        conn.execute(text("INSERT INTO model_versions VALUES ('transactions','v001','missing','missing','missing',NULL,NULL,TRUE,'2026-10-20')"))
        conn.execute(text("CREATE TABLE anomalies_history (alert_id TEXT PRIMARY KEY, timestamp_detection TEXT, origin_table TEXT, source_topic TEXT, ml_model TEXT, status TEXT, raw_event JSON)"))
    monkeypatch.setattr(pipeline, "ensure_model_versions_schema", lambda engine: None)
    main.app.dependency_overrides[pipeline_api.get_db] = lambda: engine
    main.app.dependency_overrides[anomalies_api.get_db] = lambda: engine
    yield TestClient(main.app), engine
    main.app.dependency_overrides.clear()
    engine.dispose()


def test_rf_unavailable_is_rejected_without_changing_mode(client):
    api, engine = client
    response = api.post('/api/pipelines/transactions/inference-mode', json={"inference_mode": "rf"})
    assert response.status_code == 400
    with engine.connect() as conn:
        assert conn.execute(text("SELECT inference_mode FROM pipelines_config")).scalar_one() == "if"
    assert api.get('/api/pipelines/transactions').json()['rf_available'] is False


def test_unknown_pipeline_cannot_be_created_by_mode_update(client):
    api, engine = client
    assert api.post('/api/pipelines/unknown/inference-mode', json={"inference_mode": "if"}).status_code == 404
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM pipelines_config")).scalar_one() == 1


@pytest.mark.parametrize('query', ['limit=0', 'limit=101', 'offset=-1'])
def test_invalid_pagination_returns_validation_error(client, query):
    api, _ = client
    assert api.get('/api/anomalies?' + query).status_code == 422


def test_missing_alert_returns_not_found(client):
    api, _ = client
    assert api.put('/api/anomalies/unknown/status', json={"status": "confirmed_fraud"}).status_code == 404


def test_missing_model_version_returns_not_found(client):
    api, _ = client
    assert api.post('/api/pipelines/transactions/versions/unknown/activate').status_code == 404


def test_activation_rejects_missing_artifacts(client):
    api, _ = client
    assert api.post('/api/pipelines/transactions/versions/v001/activate').status_code == 400


def test_rf_requires_the_version_preprocessor(client, tmp_path):
    api, engine = client
    rf_path = tmp_path / 'rf.pkl'
    rf_path.write_bytes(b'model')
    with engine.begin() as conn:
        conn.execute(text("UPDATE model_versions SET rf_model_path=:path"), {'path': str(rf_path)})
    assert api.post('/api/pipelines/transactions/inference-mode', json={'inference_mode': 'rf'}).status_code == 400


def test_automatic_if_only_activation_keeps_mode_and_version_consistent(client, monkeypatch):
    from src.training_pipeline.workers import model_versioning
    _, engine = client
    monkeypatch.setattr(model_versioning, 'ensure_model_versions_schema', lambda engine: None)
    with engine.begin() as conn:
        conn.execute(text("UPDATE pipelines_config SET inference_mode='rf'"))
    model_versioning.insert_model_version_record(engine, 'transactions', 'v002', {
        'translator': 't', 'if_model': 'i', 'scaler': 's', 'rf_model': None,
    }, metrics={'rf_model_trained': False}, is_active=True)
    with engine.connect() as conn:
        config = conn.execute(text("SELECT inference_mode, active_model_version FROM pipelines_config")).one()
        assert tuple(config) == ('if', 'v002')
        assert conn.execute(text("SELECT COUNT(*) FROM model_versions WHERE is_active=TRUE")).scalar_one() == 1
