import logging
import os
from dotenv import load_dotenv
from training_pipeline.workers.worker_models import train_models

load_dotenv()

TARGET_TABLE = os.getenv("TARGET_TABLE")
GROUP_ID = os.getenv("GROUP_ID")



#Training the models
train_models(target_table=TARGET_TABLE)

TRANSLATOR_PATH = f'models/{TARGET_TABLE}_translator.pkl'

if not os.path.exists(TRANSLATOR_PATH):
  logging.error(f"File not found: {TRANSLATOR_PATH}.")

