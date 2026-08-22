from types import SimpleNamespace

from anomaly_handler.src.handler import handler as handler_module


class FlakyHistoryTableEngine:
    def __init__(self, failures_before_ready):
        self.failures_before_ready = failures_before_ready
        self.attempts = 0

    def connect(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query):
        self.attempts += 1
        if self.attempts <= self.failures_before_ready:
            raise ConnectionError("database is starting")

    def commit(self):
        pass


def test_handler_retries_history_table_creation_until_database_is_ready(monkeypatch):
    engine = FlakyHistoryTableEngine(failures_before_ready=2)
    sleeps = []

    monkeypatch.setattr(handler_module, "get_db_engine", lambda: engine)
    monkeypatch.setattr(
        handler_module,
        "time",
        SimpleNamespace(sleep=lambda seconds: sleeps.append(seconds)),
        raising=False,
    )

    handler_module.AnomalyHandler(
        group_id="test-group",
        database_retry_attempts=3,
        database_retry_seconds=0.01,
    )

    assert engine.attempts == 3
    assert sleeps == [0.01, 0.01]
