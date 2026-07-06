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
        ("if", -0.05, None, False),
        ("rf", None, 0.9, True),
        ("rf", None, 0.2, False),
        ("hybrid", -0.2, 0.3, True),
        ("hybrid", -0.2, 0.5, True),
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
