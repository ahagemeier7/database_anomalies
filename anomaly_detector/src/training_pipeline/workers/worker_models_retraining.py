import os
import json
import logging
import pandas as pd
from dotenv import load_dotenv
from anomaly_detector.src.training_pipeline.db.db_internal import get_db_engine as get_db_engine_iternal
from anomaly_detector.src.training_pipeline.db.db_source import get_db_engine as get_db_engine_source

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retrain_models(target_table: str, columns_to_ignore: list = None) -> None:

  engine_source = get_db_engine_source()
  engine_internal = get_db_engine_iternal()

  try:
    df_source = pd.read_sql(f"SELECT * FROM {target_table}", engine_source)
    df_source['is_fraud'] = 0

    logging.info("Buscando histórico de auditoria no banco interno...")
    query_internal = f"""
            SELECT 
                raw_event->>'id' AS original_id, 
                status 
            FROM anomalies_history 
            WHERE origin_table = '{target_table}' 
            AND status IN ('confirmed_fraud', 'false_positive')
        """
    df_history = pd.read_sql(query_internal, engine_internal)
    
    if not df_history.empty:
      df_history['original_id'] = df_history['original_id'].astype(df_source['id'].dtype)
      
      fraudes_ids = df_history[df_history['status'] == 'confirmed_fraud']['original_id']
      falsos_pos_ids = df_history[df_history['status'] == 'false_positive']['original_id']

  except Exception as e:
    pass