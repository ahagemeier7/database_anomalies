import importlib
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "anomaly_detector"))

import src.interference_pipeline.worker as worker_module
from src.interference_pipeline.worker import Worker


@pytest.mark.parametrize(
    "mode, score_if, prob_rf, expected",
    [
        ("if", -0.2, None, True),
        ("if", -0.11, None, True),
        ("if", -0.1, None, False),
        ("if", -0.05, None, False),
        ("if", 0.05, None, False),
        ("rf", None, 0.9, True),
        ("rf", None, 0.2, False),
        ("hybrid", -0.2, 0.3, True),
        ("hybrid", -0.2, 0.5, True),
        ("hybrid", 0.2, 0.3, False),
    ],
)
def test_judge_prediction_modes(mode, score_if, prob_rf, expected):
    worker = Worker(
        target_table="test_table",
        group_id="group_test",
        columns_to_ignore=["id"],
        inference_mode=mode,
    )

    assert worker._judge_prediction(score_if=score_if, prob_rf=prob_rf) is expected


def test_load_models_returns_false_when_preprocessor_files_are_missing(monkeypatch):
    worker = Worker(
        target_table="test_table",
        group_id="group_test",
        columns_to_ignore=["id"],
        inference_mode="if",
    )

    monkeypatch.setattr(worker_module, "get_db_engine", lambda: object())
    monkeypatch.setattr(worker_module, "get_active_model_version", lambda engine, target_table: None)

    def raise_missing_preprocessor(*args, **kwargs):
        raise FileNotFoundError("translator missing")

    monkeypatch.setattr(worker_module, "DynamicPreprocessor", raise_missing_preprocessor)

    assert worker._load_models() is False


def test_missing_rf_keeps_hybrid_configuration_and_uses_if_effectively(monkeypatch):
    worker = Worker(
        target_table="test_table",
        group_id="group_test",
        columns_to_ignore=["id"],
        inference_mode="hybrid",
    )

    version_record = {
        "version": "v001",
        "translator_path": "translator.pkl",
        "if_model_path": "if_model.pkl",
        "scaler_path": "scaler.pkl",
        "rf_model_path": None,
    }

    class DummyPreprocessor:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(worker, "_sync_inference_mode_from_db", lambda: None)
    monkeypatch.setattr(worker_module, "get_db_engine", lambda: object())
    monkeypatch.setattr(
        worker_module,
        "get_active_model_version",
        lambda engine, target_table: version_record,
    )
    monkeypatch.setattr(worker_module, "DynamicPreprocessor", DummyPreprocessor)
    monkeypatch.setattr(worker_module.joblib, "load", lambda path: object())

    assert worker._load_models() is True
    assert worker.inference_mode == "hybrid"
    assert worker.effective_inference_mode == "if"
    assert worker._judge_prediction(score_if=-0.05, prob_rf=0.9) is False


def test_one_class_random_forest_has_no_fraud_probability():
    worker = Worker(
        target_table="test_table",
        group_id="group_test",
        columns_to_ignore=["id"],
        inference_mode="hybrid",
    )

    class OneClassRandomForest:
        classes_ = [0]

        def predict_proba(self, _features):
            return [[1.0]]

    worker.model_rf = OneClassRandomForest()

    assert worker._get_fraud_probability([[0.0]]) is None
