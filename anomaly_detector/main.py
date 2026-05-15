import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import os
from dotenv import load_dotenv
from src.training_pipeline.workers.worker_models_initial import train_models
from src.interference_pipeline.worker import Worker

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


  

