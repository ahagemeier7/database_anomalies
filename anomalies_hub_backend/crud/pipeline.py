from sqlalchemy import text
from sqlalchemy.engine import Engine

def get_all_pipelines(engine: Engine):
  query = text("""
    SELECT p.*,
      COALESCE(a.pending, 0) as pending_count
    FROM pipelines_config p
    LEFT JOIN (
      SELECT origin_table, COUNT(*) as pending
      FROM anomalies_history
      WHERE status = 'pending_revision'
      GROUP BY origin_table
    ) a ON a.origin_table = p.target_table
    ORDER BY p.last_startup DESC
  """)
  with engine.connect() as conn:
    result = conn.execute(query).mappings().all()
    return[dict(row) for row in result]

def get_pipeline_config(engine: Engine, target_table: str):
  query = text("SELECT columns_to_ignore FROM pipelines_config WHERE target_table = :target_table")
  with engine.connect() as conn:
    return conn.execute(query, {"target_table": target_table}).mappings().first()