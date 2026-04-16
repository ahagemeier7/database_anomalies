import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import os
from dotenv import load_dotenv
from test.training_pipeline.workers.worker_models import train_models as train_models_test
from test.interference_pipeline.workers.worker import Worker as WorkerTest
from src.training_pipeline.workers.worker_models import train_models
from src.interference_pipeline.workers.worker import Worker

load_dotenv()

TARGET_TABLE = os.getenv("TARGET_TABLE")
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
MODEL_PATH = f'models/{TARGET_TABLE}_model.pkl'

is_production = os.getenv("PRODUCTION", "False").lower() == "true"

if is_production:
    logging.info("Ambiente de PRODUÇÃO selecionado.")
    train_function = train_models
    WorkerClass = Worker
else:
    logging.info("Ambiente de TESTE selecionado.")
    train_function = train_models_test
    WorkerClass = WorkerTest


if not os.path.exists(TRANSLATOR_PATH) or not os.path.exists(MODEL_PATH):
  try:
    #Training the models
    train_function(target_table=TARGET_TABLE, columns_to_ignore=COLUMNS_TO_IGNORE)
  except Exception as e:
    logging.error(f"An error has occured while training the models: {e}")


worker = WorkerClass(
  target_table=TARGET_TABLE,
  group_id=GROUP_ID,
  columns_to_ignore=COLUMNS_TO_IGNORE,
  date_columns=DATE_COLUMNS
)


try:
  #Starting anomaly detection
  worker.start_detection()
except Exception as e:
  logging.error(f"An error has occured while searching for anomalies: {e}")

  

