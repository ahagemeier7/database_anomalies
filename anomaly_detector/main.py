import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import os
import time
from dotenv import load_dotenv
from sqlalchemy import text
from src.training_pipeline.db.db_source import get_db_engine as get_source_engine
from src.training_pipeline.workers.worker_models_initial import train_models
from src.interference_pipeline.worker import Worker

load_dotenv()

TARGET_TABLE = os.getenv("TARGET_TABLE")


def wait_for_seed_data(target_table: str, timeout: int = 600, interval: int = 3) -> None:
    """
    Poll the source database until the target table has at least one row.

    In production (table already has data) this returns instantly on the
    first poll.  In seed/test mode the table is created by the seed
    container, so the worker waits here until Phase 1 completes.
    """
    engine = get_source_engine()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {target_table}")
                ).scalar()
                if count and count > 0:
                    logging.info(
                        "Table '%s' has %d rows — proceeding with training.",
                        target_table, count,
                    )
                    return
        except Exception as exc:
            logging.warning(
                "Waiting for table '%s' to be seeded... (%s)",
                target_table, exc,
            )
        time.sleep(interval)

    raise TimeoutError(
        f"Timed out after {timeout}s waiting for data in '{target_table}'"
    )


# ------------------------------------------------------------------
# Startup gate — instant in production, waits in seed/test mode
# ------------------------------------------------------------------
wait_for_seed_data(TARGET_TABLE)

GROUP_ID = os.getenv("GROUP_ID")
COLUMNS_TO_IGNORE_ENV = os.getenv("COLUMNS_TO_IGNORE")
DATE_COLUMNS_ENV = os.getenv("DATE_COLUMNS")

if COLUMNS_TO_IGNORE_ENV:
    COLUMNS_TO_IGNORE =[col.strip() for col in COLUMNS_TO_IGNORE_ENV.split(',')]
else:
    COLUMNS_TO_IGNORE = None

if DATE_COLUMNS_ENV:
    DATE_COLUMNS =[col.strip() for col in DATE_COLUMNS_ENV.split(',')]
else:
    DATE_COLUMNS =[]

TRANSLATOR_PATH = f'models/{TARGET_TABLE}_translator.pkl'
MODEL_PATH = f'models/{TARGET_TABLE}_if_model.pkl'


if not os.path.exists(TRANSLATOR_PATH) or not os.path.exists(MODEL_PATH):
  try:
    #Training the models
    train_models(target_table=TARGET_TABLE, columns_to_ignore=COLUMNS_TO_IGNORE)
  except Exception as e:
    logging.error(f"An error has occured while training the models: {e}")


worker = Worker(
  target_table=TARGET_TABLE,
  group_id=GROUP_ID,
  columns_to_ignore=COLUMNS_TO_IGNORE,
  date_columns=DATE_COLUMNS
)



#Starting anomaly detection
worker.start_detection()


  

