"""
Seed test anomalies into the FraudOps system.

Two modes:
  --mode direct   (default) Insert directly into anomalies_history — instant, no pipeline needed.
  --mode source             Insert into credit_card_transactions — triggers full CDC→Kafka→ML pipeline.

Examples:
  python scripts/seed_anomalies.py --count 10
  python scripts/seed_anomalies.py --mode source --count 3
  python scripts/seed_anomalies.py --mode direct --count 20 --fraud-only
"""

import argparse
import random
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

# ── Connection strings ──────────────────────────────────────────────
SOURCE_DB = "postgresql://postgres:postgres@localhost:5432/db_real"
INTERNAL_DB = "postgresql://admin_fraude:senha_segura@localhost:5433/db_seguranca"

FEATURE_COLS = [f"V{i}" for i in range(1, 29)]  # V1 … V28
ALL_COLS = ["Time"] + FEATURE_COLS + ["Amount", "Class"]


# ── Helpers ─────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_raw_event(row_id: int, fraud: bool) -> dict:
    """Build a realistic raw_event payload for a single anomaly."""
    if fraud:
        # Skew features toward extreme values to look like anomalies
        features = {f"V{i}": round(random.gauss(0, 3), 4) for i in range(1, 29)}
        amount = round(random.uniform(200, 2000), 2)
        klass = 1
    else:
        features = {f"V{i}": round(random.gauss(0, 1), 4) for i in range(1, 29)}
        amount = round(random.uniform(5, 150), 2)
        klass = 0

    return {
        "id": row_id,
        "Time": round(random.uniform(0, 172800), 2),
        **features,
        "Amount": amount,
        "Class": klass,
    }


# ── Direct mode ─────────────────────────────────────────────────────

def seed_direct(count: int, fraud_only: bool) -> None:
    """Insert synthetic anomalies straight into anomalies_history."""
    conn = psycopg2.connect(INTERNAL_DB)
    cur = conn.cursor()

    # Find highest existing alert_id to avoid conflicts
    cur.execute("SELECT max(alert_id) FROM anomalies_history")
    max_id_row = cur.fetchone()[0]
    if max_id_row and max_id_row.startswith("ALRT-"):
        base = int(max_id_row.replace("ALRT-", "").replace("SEED-", "")) + 1
    else:
        base = 1

    inserted = 0
    for i in range(count):
        row_id = 900000 + i  # fake source ID range
        is_fraud = fraud_only or random.random() < 0.7  # 70% fraud if mixed
        raw_event = _generate_raw_event(row_id, fraud=is_fraud)

        alert_id = f"ALRT-SEED-{base + i:06d}"
        ts = _now_iso()

        cur.execute(
            """
            INSERT INTO anomalies_history
                (alert_id, timestamp_detection, origin_table, source_topic, ml_model, status, raw_event)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_id) DO NOTHING
            """,
            (
                alert_id,
                ts,
                "credit_card_transactions",
                "source-postgres.public.credit_card_transactions",
                "IsolationForest_v1",
                "pending_revision",
                psycopg2.extras.Json(raw_event),
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"[direct] {inserted} anomalies inserted into anomalies_history (status=pending_revision)")


# ── Source mode ─────────────────────────────────────────────────────

def seed_source(count: int, table: str) -> None:
    """Insert rows into the source table. Debezium CDC will pick them up."""
    conn = psycopg2.connect(SOURCE_DB)
    cur = conn.cursor()

    # Get max id from existing data
    cur.execute(f"SELECT max(id) FROM {table}")
    max_id = cur.fetchone()[0] or 0

    # Read a few random rows as templates
    cur.execute(f"SELECT * FROM {table} ORDER BY random() LIMIT %s", (count,))
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]

    inserted = 0
    for idx, row in enumerate(rows):
        row_dict = dict(zip(col_names, row))
        new_id = max_id + idx + 1
        row_dict["id"] = new_id

        # Perturb V-features to make them anomalous
        for col in FEATURE_COLS:
            if col in row_dict and isinstance(row_dict[col], (int, float)):
                row_dict[col] = round(row_dict[col] + random.gauss(0, 2.5), 4)

        # Increase amount
        if "Amount" in row_dict:
            row_dict["Amount"] = round(row_dict["Amount"] * random.uniform(3, 20), 2)

        # Force Class to be 1 (fraud) or random
        row_dict["Class"] = 1 if random.random() < 0.7 else 0

        columns = ", ".join(row_dict.keys())
        placeholders = ", ".join(["%s"] * len(row_dict))
        values = list(row_dict.values())

        cur.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"[source] {inserted} rows inserted into {table} (ids {max_id + 1}–{max_id + inserted})")
    print("[source] Debezium CDC will capture these → Kafka → ML detection → frontend")


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed test anomalies into FraudOps")
    parser.add_argument("--mode", choices=["direct", "source"], default="direct",
                        help="direct = insert into anomalies_history (instant); source = insert into source table (full pipeline)")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of anomalies to insert (default: 5)")
    parser.add_argument("--table", default="credit_card_transactions",
                        help="Source table name (only for --mode source)")
    parser.add_argument("--fraud-only", action="store_true",
                        help="Only insert fraud rows (only for --mode direct)")
    args = parser.parse_args()

    if args.mode == "direct":
        seed_direct(args.count, args.fraud_only)
    else:
        seed_source(args.count, args.table)


if __name__ == "__main__":
    main()
