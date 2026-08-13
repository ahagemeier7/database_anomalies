from fastapi.testclient import TestClient
import sys
import os

# Ensure the backend package 'api' can be imported as the main module expects
ROOT = os.path.dirname(os.path.dirname(__file__))
BACKEND_PATH = os.path.join(ROOT, 'anomalies_hub_backend')
sys.path.insert(0, BACKEND_PATH)
# Expose anomaly_detector package so imports like `src.training_pipeline` resolve
ANOMALY_DIR = os.path.join(ROOT, 'anomaly_detector')
sys.path.insert(0, ANOMALY_DIR)

# Provide dummy DB env vars so backend import does not exit when resolving DB engine
os.environ.setdefault('POSTGRES_USER', 'test')
os.environ.setdefault('POSTGRES_PASSWORD', 'test')
os.environ.setdefault('POSTGRES_DB', 'test')
os.environ.setdefault('POSTGRES_SERVER', 'localhost')

import anomalies_hub_backend.main as main


client = TestClient(main.app)


def test_register_and_status(monkeypatch):
    # Stub insert_model_version_record to avoid touching a real DB
    def fake_insert(engine, target_table, version, paths, metrics=None, is_active=False):
        # simple no-op to assert endpoint accepts payload
        return None

    monkeypatch.setattr('anomalies_hub_backend.api.models.mv.insert_model_version_record', fake_insert)

    payload = {
        'target_table': 'test_table',
        'version': 'v001',
        'paths': {'translator': 'p', 'if_model': 'p', 'scaler': 'p'},
        'metrics': {'samples': 10},
        'is_active': True,
    }

    resp = client.post('/api/models/register', json=payload)
    assert resp.status_code == 200
    assert resp.json().get('message') == 'registered'

    # Stub get_active_model_version to return a predictable record
    def fake_get_active(engine, target_table):
        return {
            'target_table': target_table,
            'version': 'v001',
            'translator_path': 'p',
            'if_model_path': 'p',
            'scaler_path': 'p',
            'rf_model_path': None,
            'metrics': {'samples': 10},
            'is_active': True,
            'created_at': '2026-01-01T00:00:00'
        }

    monkeypatch.setattr('anomalies_hub_backend.api.models.mv.get_active_model_version', fake_get_active)

    resp2 = client.get('/api/models/status', params={'target_table': 'test_table'})
    assert resp2.status_code == 200
    data = resp2.json()
    assert data.get('version') == 'v001'
