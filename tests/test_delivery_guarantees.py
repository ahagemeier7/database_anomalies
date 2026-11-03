import importlib
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "anomaly_detector"))
from src.interference_pipeline.producer.producer import AnomalyProducer
from anomaly_handler.src.handler import handler as handler_module


@pytest.mark.parametrize("module_name,payload", [
    ("src.interference_pipeline.consumer.consumer", {"op": "c", "after": {"id": 1}}),
    ("anomaly_handler.src.consumer.consumer", {"id": "ALRT-1"}),
])
def test_offset_is_committed_only_after_processing(monkeypatch, module_name, payload):
    module = importlib.import_module(module_name)
    commits = []
    class Message:
        def error(self): return None
        def value(self): return json.dumps(payload).encode()
    message = Message()
    class Consumer:
        def __init__(self, config):
            assert config.get("enable.auto.commit") is False
            assert config.get("enable.auto.offset.store") is False
            self.first = True
        def subscribe(self, topics): pass
        def poll(self, timeout):
            if self.first:
                self.first = False
                return message
            raise KeyboardInterrupt
        def commit(self, *, message, asynchronous):
            assert asynchronous is False
            commits.append(message)
        def close(self): pass
    monkeypatch.setattr(module, "Consumer", Consumer)
    consume = getattr(module, "consumer_kafka_stream", None) or module.anomaly_consumer_kafka
    stream = consume("test", "test")
    next(stream)
    assert commits == []
    stream.close()  # Processing failed: closing must not acknowledge this record.
    assert commits == []
    stream = consume("test", "test")
    next(stream)
    with pytest.raises(StopIteration): next(stream)
    assert commits == [message]


def test_failed_database_insert_propagates_for_reprocessing():
    class BrokenDB:
        def connect(self): raise ConnectionError("database unavailable")
    handler = handler_module.AnomalyHandler.__new__(handler_module.AnomalyHandler)
    handler.db_engine = BrokenDB()
    with pytest.raises(ConnectionError):
        handler._save_to_db({"id": "ALRT-1"})


def test_replayed_alert_preserves_human_review():
    handler = handler_module.AnomalyHandler.__new__(handler_module.AnomalyHandler)
    handler.db_engine = create_engine("sqlite://")
    handler._ensure_history_table(1, 0)
    event = {"id": "ALRT-1", "status": "pending_revision"}
    assert handler._save_to_db(event) is True
    with handler.db_engine.begin() as conn:
        conn.execute(text("UPDATE anomalies_history SET status='confirmed_fraud'"))
    assert handler._save_to_db(event) is False
    with handler.db_engine.connect() as conn:
        assert conn.execute(text("SELECT status FROM anomalies_history")).scalar_one() == "confirmed_fraud"


def test_email_is_disabled_without_opt_in(monkeypatch):
    monkeypatch.delenv("EMAIL_ENABLED", raising=False)
    engine = create_engine("sqlite://")
    monkeypatch.setattr(handler_module, "get_db_engine", lambda: engine)
    monkeypatch.setattr(handler_module, "anomaly_consumer_kafka", lambda **kwargs: iter([{"id": "ALRT-1"}]))
    smtp_attempts = []
    def unexpected_smtp(*args, **kwargs):
        smtp_attempts.append(args)
        raise AssertionError("SMTP must be disabled")
    monkeypatch.setattr(handler_module.smtplib, "SMTP_SSL", unexpected_smtp)
    handler_module.AnomalyHandler("test").handle_anomalies()
    assert smtp_attempts == []
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM anomalies_history")).scalar_one() == 1


def test_producer_propagates_delivery_failure():
    class FailedProducer:
        def produce(self, *, topic, value, callback): callback("broker unavailable", None)
        def flush(self, timeout): return 0
    producer = AnomalyProducer.__new__(AnomalyProducer)
    producer.producer = FailedProducer()
    with pytest.raises(RuntimeError, match="broker unavailable"):
        producer.send_anomaly("alerts", {"id": 1})


def test_producer_does_not_accept_unconfirmed_delivery():
    class TimedOutProducer:
        def produce(self, **kwargs): pass
        def flush(self, timeout): return 1
    producer = AnomalyProducer.__new__(AnomalyProducer)
    producer.producer = TimedOutProducer()
    with pytest.raises(TimeoutError): producer.send_anomaly("alerts", {"id": 1})
