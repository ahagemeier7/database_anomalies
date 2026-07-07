import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "anomaly_detector"))

from src.interference_pipeline.consumer import consumer as consumer_module


class FakeConsumer:
    def __init__(self, conf):
        self.conf = conf
        self.subscribed_topics = None

    def subscribe(self, topics):
        self.subscribed_topics = topics

    def poll(self, timeout=1.0):
        raise KeyboardInterrupt

    def close(self):
        pass


def test_consumer_reads_from_earliest_offset(monkeypatch):
    captured = {}

    class CaptureConsumer(FakeConsumer):
        def __init__(self, conf):
            super().__init__(conf)
            captured["conf"] = conf

    monkeypatch.setattr(consumer_module, "Consumer", CaptureConsumer)
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    list(consumer_module.consumer_kafka_stream(topic="test-topic", group_id="group-test"))

    assert captured["conf"]["auto.offset.reset"] == "earliest"
