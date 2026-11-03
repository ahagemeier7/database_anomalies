import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'anomaly_detector'))
from src.training_pipeline.workers import worker_models_retraining as retraining
from src.training_pipeline.workers import worker_models_initial as initial
from src.training_pipeline.workers import model_versioning as versioning


class Connection:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, *args, **kwargs): pass
    def commit(self): pass


class Engine:
    def connect(self): return Connection()


@pytest.mark.parametrize('normal,fraud,validated', [(1, 1, False), (2, 2, False), (2, 3, False), (3, 3, True), (0, 3, False)])
def test_retraining_handles_small_review_sets(monkeypatch, normal, fraud, validated):
    size = normal + fraud
    labels = [0] * normal + [1] * fraud
    source = pd.DataFrame({'id': range(1, size+1), 'Class': labels, 'Amount': range(size)})
    history = pd.DataFrame({'original_id': list(map(str, source.id)), 'status': ['false_positive' if x == 0 else 'confirmed_fraud' for x in labels]})
    monkeypatch.setattr(retraining, 'get_db_engine_source', Engine)
    monkeypatch.setattr(retraining, 'get_db_engine_internal', Engine)
    monkeypatch.setattr(retraining.pd, 'read_sql', lambda query, engine, **kwargs: history.copy() if 'anomalies_history' in str(query) else source.copy())
    saved = {}
    def save(**kwargs):
        saved.update(kwargs)
        return {'version': 'v001', 'paths': {}}
    metrics = {}
    monkeypatch.setattr(retraining, 'save_versioned_models', save)
    monkeypatch.setattr(retraining, 'insert_model_version_record', lambda *args, **kwargs: metrics.update(kwargs['metrics']))
    retraining.retrain_hybrid_models('creditcard_transactions', ['id', 'Class'])
    assert metrics['rf_model_trained'] is (normal > 0 and fraud > 0)
    assert ('f1_score' in metrics) is validated
    if normal > 0:
        assert list(saved['rf_model'].classes_) == [0, 1]


def test_rf_validation_preprocessor_does_not_fit_test_rows(monkeypatch):
    source = pd.DataFrame({'id': range(20), 'Amount': range(20)})
    history = pd.DataFrame({'original_id': list(map(str, source.id)), 'status': ['false_positive']*10 + ['confirmed_fraud']*10})
    monkeypatch.setattr(retraining, 'get_db_engine_source', Engine)
    monkeypatch.setattr(retraining, 'get_db_engine_internal', Engine)
    monkeypatch.setattr(retraining.pd, 'read_sql', lambda query, engine, **kwargs: history.copy() if 'anomalies_history' in str(query) else source.copy())
    fit_sizes = []
    class ObservedScaler(StandardScaler):
        def fit(self, x, y=None, **kwargs):
            fit_sizes.append(len(x))
            return super().fit(x, y, **kwargs)
    monkeypatch.setattr(retraining, 'StandardScaler', ObservedScaler)
    monkeypatch.setattr(retraining, 'save_versioned_models', lambda **kwargs: {'version': 'v001', 'paths': {}})
    monkeypatch.setattr(retraining, 'insert_model_version_record', lambda *args, **kwargs: None)
    retraining.retrain_hybrid_models('transactions', ['id'])
    assert 16 in fit_sizes  # Validation transformation learned on the 80% training split.


def test_absent_rf_has_no_recorded_artifact_path(tmp_path):
    translator = DictVectorizer(sparse=False)
    x = translator.fit_transform([{'a': 1.0}, {'a': 2.0}])
    scaler = StandardScaler().fit(x)
    forest = IsolationForest(random_state=42).fit(x)
    result = versioning.save_versioned_models('transactions', str(tmp_path), translator, forest, scaler)
    assert result['paths']['rf_model'] is None


def test_bootstrap_retrains_when_db_metadata_is_missing(monkeypatch, tmp_path):
    # Existing files alone must not bypass database registration.
    for name in ('translator', 'if_model', 'scaler'):
        (tmp_path / f'transactions_{name}.pkl').write_bytes(b'old model')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(initial, 'get_db_engine_internal', Engine)
    monkeypatch.setattr(versioning, 'get_active_model_version', lambda *args: None)
    trained = []
    monkeypatch.setattr(initial, 'train_models', lambda **kwargs: trained.append(kwargs['target_table']))
    initial.ensure_initial_models('transactions', ['id'])
    assert trained == ['transactions']
