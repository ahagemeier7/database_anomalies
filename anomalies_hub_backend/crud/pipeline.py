import json
from sqlalchemy import text
from sqlalchemy.engine import Engine

def ensure_model_versions_schema(engine: Engine):
  create_table_query = text("""
    CREATE TABLE IF NOT EXISTS model_versions (
      id SERIAL PRIMARY KEY,
      target_table VARCHAR(100) NOT NULL,
      version VARCHAR(50) NOT NULL,
      translator_path TEXT NOT NULL,
      if_model_path TEXT NOT NULL,
      scaler_path TEXT NOT NULL,
      rf_model_path TEXT,
      metrics JSONB,
      is_active BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(target_table, version)
    );
  """)

  alter_table_query = text("""
    ALTER TABLE pipelines_config
    ADD COLUMN IF NOT EXISTS active_model_version VARCHAR(50),
    ADD COLUMN IF NOT EXISTS inference_mode VARCHAR(50) DEFAULT 'hybrid';
  """)

  with engine.connect() as conn:
    conn.execute(create_table_query)
    conn.execute(alter_table_query)
    conn.commit()


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


def insert_model_version_record(engine: Engine, target_table: str, version: str, paths: dict, metrics: dict | None = None, is_active: bool = False):
  ensure_model_versions_schema(engine)
  query = text("""
    INSERT INTO model_versions (
      target_table,
      version,
      translator_path,
      if_model_path,
      scaler_path,
      rf_model_path,
      metrics,
      is_active
    ) VALUES (
      :target_table,
      :version,
      :translator_path,
      :if_model_path,
      :scaler_path,
      :rf_model_path,
      :metrics::jsonb,
      :is_active
    )
    ON CONFLICT (target_table, version) DO UPDATE SET
      translator_path = EXCLUDED.translator_path,
      if_model_path = EXCLUDED.if_model_path,
      scaler_path = EXCLUDED.scaler_path,
      rf_model_path = EXCLUDED.rf_model_path,
      metrics = EXCLUDED.metrics,
      is_active = EXCLUDED.is_active,
      created_at = CURRENT_TIMESTAMP;
  """)

  with engine.connect() as conn:
    conn.execute(query, {
      "target_table": target_table,
      "version": version,
      "translator_path": paths["translator"],
      "if_model_path": paths["if_model"],
      "scaler_path": paths["scaler"],
      "rf_model_path": paths.get("rf_model"),
      "metrics": json.dumps(metrics) if metrics is not None else None,
      "is_active": is_active,
    })
    conn.commit()


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


def get_active_model_version(engine: Engine, target_table: str):
  ensure_model_versions_schema(engine)
  query = text(
    "SELECT target_table, version, translator_path, if_model_path, scaler_path, rf_model_path, metrics, is_active, created_at "
    "FROM model_versions WHERE target_table = :target_table AND is_active = true LIMIT 1"
  )
  with engine.connect() as conn:
    row = conn.execute(query, {"target_table": target_table}).mappings().first()
    return _parse_metrics(dict(row)) if row else None


def get_model_version(engine: Engine, target_table: str, version: str):
  ensure_model_versions_schema(engine)
  query = text(
    "SELECT target_table, version, translator_path, if_model_path, scaler_path, rf_model_path, metrics, is_active, created_at "
    "FROM model_versions WHERE target_table = :target_table AND version = :version LIMIT 1"
  )
  with engine.connect() as conn:
    row = conn.execute(query, {"target_table": target_table, "version": version}).mappings().first()
    return _parse_metrics(dict(row)) if row else None


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