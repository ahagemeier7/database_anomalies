import pandas as pd
import pytest
from sqlalchemy import create_engine

from scripts.startup_datasets_seed import automated_seed as seed
from scripts import seed_anomalies as auxiliary


@pytest.mark.parametrize('existing_frauds', [0, 1])
def test_seed_resumes_without_replacing_existing_source(monkeypatch, tmp_path, existing_frauds):
    dataset = pd.DataFrame({'Class': [0, 0, 1], 'Amount': [5., 10., 100.]})
    csv = tmp_path / 'dataset.csv'
    dataset.to_csv(csv, index=False)
    engine = create_engine('sqlite://')
    existing = dataset.iloc[:2+existing_frauds].copy()
    existing['id'] = range(1, len(existing)+1)
    existing.to_sql('transactions', engine, index=False)
    monkeypatch.setattr(seed, 'wait_for_pipeline_ready', lambda *args: True)
    cfg = {'target_table': 'transactions', 'fraud_column': 'Class', 'csv_file': str(csv), 'poll_timeout': 1, 'poll_interval': 0}
    seed.seed_dataset(cfg, engine, object())
    result = pd.read_sql_table('transactions', engine)
    assert len(result) == 3
    assert result.id.tolist() == [1, 2, 3]
    assert result.Amount.tolist() == [5., 10., 100.]


def test_auxiliary_source_seed_uses_active_table_by_default(monkeypatch):
    import sys
    called = []
    monkeypatch.setattr(sys, 'argv', ['seed_anomalies.py', '--mode', 'source'])
    monkeypatch.setattr(auxiliary, 'seed_source', lambda count, table: called.append(table))
    auxiliary.main()
    assert called == ['creditcard_transactions']
