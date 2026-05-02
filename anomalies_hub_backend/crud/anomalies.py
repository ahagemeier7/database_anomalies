from sqlalchemy import text
from sqlalchemy.engine import Engine

def get_anomalies_by_status(engine: Engine, status: str, limit: int = 50):
  query = text("""
    SELECT alert_id, timestamp_detection, origin_table, ml_model, status, raw_event 
    FROM anomalies_history 
    WHERE status = :status
    ORDER BY timestamp_detection DESC
    LIMIT :limit
  """)
  with engine.connect() as conn:
    result = conn.execute(query, {"status": status, "limit": limit}).mappings().all()
    return [dict(row) for row in result]

def update_status(engine: Engine, alert_id: str, status: str):
  query = text("UPDATE anomalies_history SET status = :status WHERE alert_id = :alert_id")
  with engine.connect() as conn:
    conn.execute(query, {"status": status, "alert_id": alert_id})
    conn.commit()