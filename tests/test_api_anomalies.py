from fastapi import HTTPException
from anomalies_hub_backend.api import anomalies as api_anomalies
from anomalies_hub_backend.schemas.schemas import StatusUpdatePayload


def test_fetch_anomalies_success(monkeypatch):
    fake_items = [{"id": "a1"}, {"id": "a2"}]
    fake_total = 2

    monkeypatch.setattr(
        api_anomalies.anomalies,
        "get_anomalies_by_status",
        lambda db, status, limit=25, offset=0, origin_table=None: fake_items,
    )
    monkeypatch.setattr(
        api_anomalies.anomalies,
        "count_anomalies_by_status",
        lambda db, status, origin_table=None: fake_total,
    )

    result = api_anomalies.fetch_anomalies(db="fake_db")
    assert result["anomalies"] == fake_items
    assert result["total"] == fake_total


def test_update_anomaly_invalid_status():
    payload = StatusUpdatePayload(status="not_valid")
    try:
        api_anomalies.update_anomaly("alert1", payload, db="fake_db")
        assert False, "Expected HTTPException for invalid status"
    except HTTPException as e:
        assert e.status_code == 400


def test_fetch_dashboard_stats(monkeypatch):
    fake_stats = {"total": 10}
    monkeypatch.setattr(api_anomalies.anomalies, "get_dashboard_stats", lambda db: fake_stats)
    result = api_anomalies.fetch_dashboard_stats(db="fake_db")
    assert result == fake_stats
