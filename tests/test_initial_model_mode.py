import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DETECTOR_PATH = ROOT / "anomaly_detector"
if str(DETECTOR_PATH) not in sys.path:
    sys.path.insert(0, str(DETECTOR_PATH))

from src.interference_pipeline.worker import Worker
from src.training_pipeline.workers import worker_models_initial as initial_training
from src.training_pipeline.workers import worker_models_retraining as retraining


class RecordingConnection:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))

    def commit(self):
        pass


class RecordingEngine:
    def __init__(self):
        self.connection = RecordingConnection()

    def connect(self):
        return self.connection


def test_initial_training_registers_isolation_forest_mode(monkeypatch):
    source_engine = object()
    internal_engine = RecordingEngine()
    dataset = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "Class": [0, 0, 0, 0],
            "amount": [10.0, 12.0, 14.0, 16.0],
        }
    )

    monkeypatch.setattr(initial_training, "get_db_engine", lambda: source_engine)
    monkeypatch.setattr(initial_training, "get_db_engine_internal", lambda: internal_engine)
    monkeypatch.setattr(initial_training.pd, "read_sql", lambda *_args, **_kwargs: dataset)
    monkeypatch.setattr(
        initial_training,
        "save_versioned_models",
        lambda **_kwargs: {"version": "v001", "paths": {"translator": "t", "if_model": "i", "scaler": "s"}},
    )
    monkeypatch.setattr(initial_training, "insert_model_version_record", lambda *_args, **_kwargs: None)

    initial_training.train_models("transactions", columns_to_ignore=["id", "Class"])

    assert any(
        "inference_mode" in statement and params.get("inference_mode") == "if"
        for statement, params in internal_engine.connection.executed
    )


def test_worker_registration_keeps_mode_already_persisted_for_pipeline(monkeypatch):
    engine = RecordingEngine()
    worker = Worker(
        target_table="transactions",
        group_id="test-group",
        columns_to_ignore=["id"],
        inference_mode="hybrid",
    )

    monkeypatch.setattr("src.interference_pipeline.worker.get_db_engine", lambda: engine)

    worker._register_pipeline()

    upsert_statement = engine.connection.executed[1][0]
    assert "inference_mode = COALESCE(pipelines_config.inference_mode, EXCLUDED.inference_mode)" in upsert_statement


def test_retraining_requires_confirmed_fraud_and_false_positive():
    assert retraining.has_binary_review_labels([1, 1]) is False
    assert retraining.has_binary_review_labels([0, 1]) is True
