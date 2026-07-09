import json
import sys
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Import shared model versioning functions from the mounted volume
sys.path.append('/app')
from src.training_pipeline.workers.model_versioning import (
    ensure_model_versions_schema,
    get_model_version,
    get_active_model_version,
    insert_model_version_record,
)


def get_all_pipelines(engine: Engine):
  try:
    query = text("""
      SELECT p.target_table,
        p.pipeline_name,
        p.columns_to_ignore,
        p.date_columns,
        p.inference_mode,
        p.status,
        p.last_startup,
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
      return [dict(row) for row in result]
  except Exception:
    with engine.connect() as conn:
      result = conn.execute(
        text("SELECT target_table, pipeline_name, columns_to_ignore, date_columns, inference_mode, status, last_startup FROM pipelines_config ORDER BY last_startup DESC")
      ).mappings().all()
      pipelines = [dict(row) for row in result]
      for pipeline in pipelines:
        pipeline["pending_count"] = 0
      return pipelines

def get_pipeline_config(engine: Engine, target_table: str):
  query = text("SELECT columns_to_ignore, inference_mode FROM pipelines_config WHERE target_table = :target_table")
  with engine.connect() as conn:
    return conn.execute(query, {"target_table": target_table}).mappings().first()


def update_pipeline_inference_mode(engine: Engine, target_table: str, inference_mode: str):
  ensure_model_versions_schema(engine)
  normalized_mode = str(inference_mode or '').strip().lower()
  if normalized_mode not in {'if', 'rf', 'hybrid'}:
    raise ValueError("inference_mode must be one of: if, rf, hybrid")

  with engine.begin() as conn:
    conn.execute(
      text("""
        INSERT INTO pipelines_config (target_table, inference_mode)
        VALUES (:target_table, :inference_mode)
        ON CONFLICT (target_table)
        DO UPDATE SET inference_mode = EXCLUDED.inference_mode
      """),
      {"target_table": target_table, "inference_mode": normalized_mode}
    )


def _parse_metrics(row: dict) -> dict:
  """Parse metrics field that may be stored as a JSON string or already a dict."""
  if row.get("metrics") is not None and isinstance(row["metrics"], str):
    try:
      row["metrics"] = json.loads(row["metrics"])
    except (json.JSONDecodeError, TypeError):
      pass
  return row


def get_model_versions(engine: Engine, target_table: str):
  ensure_model_versions_schema(engine)
  query = text(
    "SELECT target_table, version, translator_path, if_model_path, scaler_path, rf_model_path, metrics, is_active, created_at "
    "FROM model_versions WHERE target_table = :target_table ORDER BY created_at DESC"
  )
  with engine.connect() as conn:
    result = conn.execute(query, {"target_table": target_table}).mappings().all()
    return [_parse_metrics(dict(row)) for row in result]


def activate_model_version(engine: Engine, target_table: str, version: str):
  ensure_model_versions_schema(engine)
  with engine.begin() as conn:
    version_exists = conn.execute(
      text("SELECT 1 FROM model_versions WHERE target_table = :target_table AND version = :version"),
      {"target_table": target_table, "version": version}
    ).scalar_one_or_none()

    if not version_exists:
      raise ValueError("Model version not found")

    conn.execute(
      text("UPDATE model_versions SET is_active = false WHERE target_table = :target_table"),
      {"target_table": target_table}
    )

    conn.execute(
      text("UPDATE model_versions SET is_active = true WHERE target_table = :target_table AND version = :version"),
      {"target_table": target_table, "version": version}
    )

    conn.execute(
      text("UPDATE pipelines_config SET active_model_version = :version WHERE target_table = :target_table"),
      {"target_table": target_table, "version": version}
    )