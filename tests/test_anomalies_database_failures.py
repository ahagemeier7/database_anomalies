import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError


ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "anomalies_hub_backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_SERVER", "localhost")

from crud import anomalies
from api import anomalies as anomalies_api


class UnavailableConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, *_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, RuntimeError("database is down"))


class UnavailableEngine:
    def connect(self):
        return UnavailableConnection()


def test_anomaly_query_raises_database_unavailable_error_when_database_is_down():
    with pytest.raises(anomalies.DatabaseUnavailableError):
        anomalies.get_anomalies_by_status(
            UnavailableEngine(),
            status="pending_revision",
        )


def test_anomalies_endpoint_returns_503_when_database_is_down():
    with pytest.raises(HTTPException) as exc_info:
        anomalies_api.fetch_anomalies(db=UnavailableEngine())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Database temporarily unavailable."
