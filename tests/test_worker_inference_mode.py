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


def test_failed_reload_preserves_previous_working_models(monkeypatch):
    worker = Worker("test_table", "test", ["id"], inference_mode="rf")
    previous_preprocessor, previous_if = object(), object()
    worker.preprocessor = previous_preprocessor
    worker.model_if = previous_if
    worker.effective_inference_mode = "if"
    worker.last_active_version = "v001"
    monkeypatch.setattr(worker, "_sync_inference_mode_from_db", lambda: None)
    monkeypatch.setattr(worker_module, "get_db_engine", lambda: object())
    monkeypatch.setattr(worker_module, "get_active_model_version", lambda *args: {
        "version": "v002", "translator_path": "new.pkl", "if_model_path": "new_if.pkl",
        "scaler_path": "new_scaler.pkl", "rf_model_path": None,
    })
    monkeypatch.setattr(worker_module, "DynamicPreprocessor", lambda **kwargs: object())
    monkeypatch.setattr(worker_module.joblib, "load", lambda path: object())
    assert worker._load_models() is False
    assert worker.preprocessor is previous_preprocessor
    assert worker.model_if is previous_if
    assert worker.effective_inference_mode == "if"
    assert worker.last_active_version == "v001"


def test_switch_to_if_clears_previous_rf(monkeypatch):
    worker = Worker("test_table", "test", ["id"], inference_mode="if")
    worker.model_rf = object()
    monkeypatch.setattr(worker, "_sync_inference_mode_from_db", lambda: None)
    monkeypatch.setattr(worker_module, "get_db_engine", lambda: object())
    monkeypatch.setattr(worker_module, "get_active_model_version", lambda *args: None)
    monkeypatch.setattr(worker_module, "DynamicPreprocessor", lambda **kwargs: object())
    monkeypatch.setattr(worker_module.joblib, "load", lambda path: object())
    assert worker._load_models() is True
    assert worker.model_rf is None


def test_explicit_missing_scaler_cannot_silently_change_preprocessing(tmp_path):
    import joblib
    from sklearn.feature_extraction import DictVectorizer
    from src.interference_pipeline.preprocessing_data.preprocess_data import DynamicPreprocessor
    translator = tmp_path / 'translator.pkl'
    joblib.dump(DictVectorizer().fit([{'amount': 1.0}]), translator)
    with pytest.raises(FileNotFoundError):
        DynamicPreprocessor('transactions', [], str(translator), str(tmp_path / 'missing_scaler.pkl'))


def test_failed_mode_change_is_retried_on_next_event(monkeypatch):
    class ConfigEngine:
        def connect(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, *args): return self
        def mappings(self): return self
        def first(self): return {'inference_mode': 'if'}
    worker = Worker('transactions', 'test', ['id'], inference_mode='hybrid')
    worker.preprocessor = object()
    worker.effective_inference_mode = 'hybrid'
    worker.loaded_inference_mode = 'hybrid'
    monkeypatch.setattr(worker_module, 'get_db_engine', ConfigEngine)
    reads = []
    def read_active(*args):
        reads.append(True)
        if len(reads) == 1: raise ConnectionError('transient metadata failure')
        return None
    monkeypatch.setattr(worker_module, 'get_active_model_version', read_active)
    monkeypatch.setattr(worker_module, 'DynamicPreprocessor', lambda **kwargs: object())
    monkeypatch.setattr(worker_module.joblib, 'load', lambda path: object())
    worker._sync_inference_mode_from_db(reload_models=True)
    assert worker.effective_inference_mode == 'hybrid'
    worker._sync_inference_mode_from_db(reload_models=True)
    assert worker.effective_inference_mode == 'if'
