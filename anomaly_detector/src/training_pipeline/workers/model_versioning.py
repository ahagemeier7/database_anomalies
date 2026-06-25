import glob
import json
import logging
import os
import re
from typing import Dict, Optional
from datetime import datetime
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.engine import Engine

import joblib


def get_next_model_version(target_table: str, models_dir: str) -> int:
    pattern = os.path.join(models_dir, f"{target_table}_v*_translator.pkl")
    versions = []
    for path in glob.glob(pattern):
        match = re.search(rf"{re.escape(target_table)}_v(\d+)_translator\.pkl$", os.path.basename(path))
        if match:
            versions.append(int(match.group(1)))

    return max(versions, default=0) + 1


def build_model_paths(target_table: str, models_dir: str, version: int) -> Dict[str, str]:
    version_tag = f"v{version:03d}"
    return {
        "version": version_tag,
        "translator": os.path.join(models_dir, f"{target_table}_{version_tag}_translator.pkl"),
        "if_model": os.path.join(models_dir, f"{target_table}_{version_tag}_if_model.pkl"),
        "scaler": os.path.join(models_dir, f"{target_table}_{version_tag}_scaler.pkl"),
        "rf_model": os.path.join(models_dir, f"{target_table}_{version_tag}_rf_model.pkl"),
        "latest_translator": os.path.join(models_dir, f"{target_table}_translator.pkl"),
        "latest_if_model": os.path.join(models_dir, f"{target_table}_if_model.pkl"),
        "latest_scaler": os.path.join(models_dir, f"{target_table}_scaler.pkl"),
        "latest_rf_model": os.path.join(models_dir, f"{target_table}_rf_model.pkl"),
    }


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
      ADD COLUMN IF NOT EXISTS active_model_version VARCHAR(50);
    """)

    with engine.connect() as conn:
        conn.execute(create_table_query)
        conn.execute(alter_table_query)
        conn.commit()


def save_versioned_models(
    target_table: str,
    models_dir: str,
    translator: DictVectorizer,
    isolation_forest: IsolationForest,
    scaler: StandardScaler,
    rf_model: Optional[RandomForestClassifier] = None,
) -> Dict[str, Dict[str, str]]:
    os.makedirs(models_dir, exist_ok=True)
    version = get_next_model_version(target_table, models_dir)
    paths = build_model_paths(target_table, models_dir, version)

    joblib.dump(translator, paths["translator"])
    joblib.dump(translator, paths["latest_translator"])

    joblib.dump(isolation_forest, paths["if_model"])
    joblib.dump(isolation_forest, paths["latest_if_model"])

    joblib.dump(scaler, paths["scaler"])
    joblib.dump(scaler, paths["latest_scaler"])

    if rf_model is not None:
        joblib.dump(rf_model, paths["rf_model"])
        joblib.dump(rf_model, paths["latest_rf_model"])

    version_tag = paths["version"]
    logging.info(
        "Saved version %s for table '%s' in %s",
        version_tag,
        target_table,
        models_dir,
    )

    return {"version": version_tag, "paths": paths}


def insert_model_version_record(
    engine: Engine,
    target_table: str,
    version: str,
    paths: dict,
    metrics: dict | None = None,
    is_active: bool = False,
):
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
        :metrics,
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

    metrics_json = json.dumps(metrics) if metrics is not None else None

    with engine.connect() as conn:
        conn.execute(query, {
            "target_table": target_table,
            "version": version,
            "translator_path": paths["translator"],
            "if_model_path": paths["if_model"],
            "scaler_path": paths["scaler"],
            "rf_model_path": paths.get("rf_model"),
            "metrics": metrics_json,
            "is_active": is_active,
        })
        conn.commit()


def get_model_version(engine: Engine, target_table: str, version: str):
    ensure_model_versions_schema(engine)
    query = text(
        "SELECT target_table, version, translator_path, if_model_path, scaler_path, rf_model_path, metrics, is_active, created_at "
        "FROM model_versions WHERE target_table = :target_table AND version = :version LIMIT 1"
    )
    with engine.connect() as conn:
        return conn.execute(query, {"target_table": target_table, "version": version}).mappings().first()


def get_active_model_version(engine: Engine, target_table: str):
    ensure_model_versions_schema(engine)
    query = text(
        "SELECT target_table, version, translator_path, if_model_path, scaler_path, rf_model_path, metrics, is_active, created_at "
        "FROM model_versions WHERE target_table = :target_table AND is_active = true LIMIT 1"
    )
    with engine.connect() as conn:
        return conn.execute(query, {"target_table": target_table}).mappings().first()
