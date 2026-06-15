"""
Automated seed script for FraudOps pipeline testing.

Replaces the manual input()-based flow with automatic polling:
  1. Insert NORMAL rows into the source table (target_table).
  2. Poll postgres-internal.pipelines_config until the worker registers itself
     (meaning train_models has finished on normal-only data).
  3. Insert FRAUD rows so the running worker can detect them via CDC.

Configurable entirely through environment variables — see read_config().
"""

import os
import sys
import time
import logging

import pandas as pd
from sqlalchemy import create_engine, Engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("automated_seed")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def read_config() -> dict:
    """Build connection dicts from environment variables."""
    source = {
        "host":     _env("POSTGRES_SOURCE_HOST", "postgres-source"),
        "port":     _env("POSTGRES_SOURCE_PORT", "5432"),
        "user":     _env("POSTGRES_SOURCE_USER", "postgres"),
        "password": _env("POSTGRES_SOURCE_PASSWORD", "postgres"),
        "database": _env("POSTGRES_SOURCE_DB", "db_real"),
    }
    internal = {
        "host":     _env("POSTGRES_INTERNAL_HOST", "postgres-internal"),
        "port":     _env("POSTGRES_INTERNAL_PORT", "5432"),
        "user":     _env("POSTGRES_INTERNAL_USER", "admin_fraude"),
        "password": _env("POSTGRES_INTERNAL_PASSWORD", "senha_segura"),
        "database": _env("POSTGRES_INTERNAL_DB", "db_seguranca"),
    }
    return {
        "source": source,
        "internal": internal,
        "target_table":   _env("TARGET_TABLE", "insurance_claims"),
        "fraud_column":   _env("FRAUD_COLUMN", "FraudFound_P"),
        "csv_file":       _env("CSV_FILE", "insurance_fraud.csv"),
        "poll_interval":  int(_env("POLL_INTERVAL", "3")),
        "poll_timeout":   int(_env("POLL_TIMEOUT", "600")),
    }


def _build_url(db: dict) -> str:
    return (
        f"postgresql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['database']}"
    )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def wait_for_pipeline_ready(
    engine: Engine,
    target_table: str,
    timeout: int,
    interval: int,
) -> bool:
    """
    Poll the *internal* database's `pipelines_config` table until the row
    for `target_table` shows status = 'active', meaning the worker has
    finished training and registered itself.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT status FROM pipelines_config "
                        "WHERE target_table = :tbl"
                    ),
                    {"tbl": target_table},
                ).fetchone()

                if row and row[0] == "active":
                    log.info(
                        "Worker pipeline '%s' is active – proceeding to Phase 2.",
                        target_table,
                    )
                    return True
        except Exception as exc:
            log.warning("Waiting for pipelines_config table... (%s)", exc)

        time.sleep(interval)

    return False


def seed_dataset(
    cfg: dict,
    source_engine: Engine,
    internal_engine: Engine,
) -> None:
    target_table = cfg["target_table"]
    fraud_col    = cfg["fraud_column"]
    csv_file     = cfg["csv_file"]

    # Locate CSV next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path   = os.path.join(script_dir, csv_file)

    if not os.path.exists(csv_path):
        log.error("CSV file not found: %s — skipping dataset '%s'.",
                  csv_path, target_table)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load & split
    # ------------------------------------------------------------------
    log.info("Loading %s ...", csv_path)
    df = pd.read_csv(csv_path)

    df_normal = df[df[fraud_col] == 0].reset_index(drop=True)
    df_fraud  = df[df[fraud_col] == 1].reset_index(drop=True)

    log.info("Normal rows: %d  |  Fraud rows: %d", len(df_normal), len(df_fraud))

    # ------------------------------------------------------------------
    # Phase 1 – insert NORMAL rows
    # ------------------------------------------------------------------
    df_normal["id"] = range(1, len(df_normal) + 1)

    log.info("Phase 1: inserting %d normal rows into %s ...",
             len(df_normal), target_table)

    df_normal.to_sql(target_table, source_engine, if_exists="replace", index=False)

    with source_engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {target_table} ADD PRIMARY KEY (id);"))
        conn.commit()

    log.info("Phase 1 complete – %d normal rows inserted.", len(df_normal))

    # ------------------------------------------------------------------
    # Wait for worker pipeline to register
    # ------------------------------------------------------------------
    log.info("Waiting for worker pipeline on table '%s' (timeout=%ds)...",
             target_table, cfg["poll_timeout"])

    if not wait_for_pipeline_ready(
        internal_engine,
        target_table,
        cfg["poll_timeout"],
        cfg["poll_interval"],
    ):
        log.error(
            "Timed out after %ds waiting for pipeline '%s'. "
            "Is the worker running?",
            cfg["poll_timeout"],
            target_table,
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 2 – insert FRAUD rows
    # ------------------------------------------------------------------
    df_fraud["id"] = range(
        len(df_normal) + 1,
        len(df_normal) + len(df_fraud) + 1,
    )

    log.info("Phase 2: inserting %d fraud rows into %s ...",
             len(df_fraud), target_table)

    df_fraud.to_sql(target_table, source_engine, if_exists="append", index=False)

    log.info("Phase 2 complete – %d fraud rows inserted.", len(df_fraud))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = read_config()

    source_url   = _build_url(cfg["source"])
    internal_url = _build_url(cfg["internal"])

    log.info("Connecting to source DB:   %s:%s/%s",
             cfg["source"]["host"], cfg["source"]["port"],
             cfg["source"]["database"])
    log.info("Connecting to internal DB: %s:%s/%s",
             cfg["internal"]["host"], cfg["internal"]["port"],
             cfg["internal"]["database"])

    source_engine   = create_engine(source_url)
    internal_engine = create_engine(internal_url)

    seed_dataset(cfg, source_engine, internal_engine)

    log.info("🎉 Seed complete for '%s'.", cfg["target_table"])


if __name__ == "__main__":
    main()
