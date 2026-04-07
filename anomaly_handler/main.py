import os
import logging
from dotenv import load_dotenv
from anomaly_handler.test.handler.handler import AnomalyHandler

load_dotenv()

GROUP_ID= os.getenv("GROUP_ID")

handler = AnomalyHandler(group_id=GROUP_ID)

try:
  handler.handle_anomalies()
except Exception as e:
  logging.error(f"An error has occured during the anomaly handing: {e}")