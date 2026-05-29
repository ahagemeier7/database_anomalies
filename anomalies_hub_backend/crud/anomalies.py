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


def get_dashboard_stats(engine: Engine):
  """Calculate the ML stats for the graphs"""
  
  query_counts = text("""
    SELECT 
      COUNT(*) as total_alerts,
      COUNT(CASE WHEN status = 'pending_revision' THEN 1 END) as pending_reviews,
      COUNT(CASE WHEN status = 'confirmed_fraud' THEN 1 END) as confirmed_frauds,
      COUNT(CASE WHEN status = 'false_positive' THEN 1 END) as false_positives
    FROM anomalies_history;
  """)
  
  query_chart = text("""
    SELECT 
      DATE(timestamp_detection) as date,
      COUNT(CASE WHEN status = 'confirmed_fraud' THEN 1 END) as frauds,
      COUNT(CASE WHEN status = 'false_positive' THEN 1 END) as false_positives
    FROM anomalies_history
    GROUP BY DATE(timestamp_detection)
    ORDER BY date ASC
    LIMIT 7;
  """)

  with engine.connect() as conn:
    counts = conn.execute(query_counts).mappings().first()
    chart_data = conn.execute(query_chart).mappings().all()

  confirmed = counts['confirmed_frauds'] or 0
  false_pos = counts['false_positives'] or 0

  precision = 0.0
  if (confirmed + false_pos) > 0:
    precision = confirmed / (confirmed + false_pos)

  return {
    "total_alerts": counts['total_alerts'] or 0,
    "pending_reviews": counts['pending_reviews'] or 0,
    "confirmed_frauds": confirmed,
    "false_positives": false_pos,
    "model_metrics": {
      "precision": round(precision * 100, 1),
    },
    "history_chart": [dict(row) for row in chart_data]
  }