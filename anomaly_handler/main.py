import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from dotenv import load_dotenv
from src.handler.handler import AnomalyHandler as AnomalyHandlerTest
from src.handler.handler import AnomalyHandler

load_dotenv()

GROUP_ID= os.getenv("KAFKA_GROUP_ID")

is_production = os.getenv("PRODUCTION", "False").lower() == "true"

if is_production:
    logging.info("Ambiente de PRODUÇÃO selecionado.")
    AnomalyHandlerClass = AnomalyHandler
else:
    logging.info("Ambiente de TESTE selecionado.")
    AnomalyHandlerClass = AnomalyHandlerTest

handler = AnomalyHandlerClass(group_id=GROUP_ID)

try:
  handler.handle_anomalies()
except Exception as e:
  logging.error(f"An error has occured during the anomaly handling: {e}")