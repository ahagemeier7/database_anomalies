import os
import joblib
import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy import text
from ..training_pipeline.db.db_internal import get_db_engine
from .preprocessing_data.preprocess_data import DynamicPreprocessor
from .consumer.consumer import consumer_kafka_stream
from .producer.producer import AnomalyProducer
from sklearn.ensemble import IsolationForest,RandomForestClassifier


class Worker:

  def __init__(self,target_table:str,group_id:str,columns_to_ignore: List[str],date_columns:List[str] = None):
    self.target_table = target_table

    self.group_id = group_id
    self.columns_to_ignore = columns_to_ignore or ['id'] 
    self.date_columns = date_columns or []
    self.anomaly_producer = AnomalyProducer()
    
    self.preprocessor: DynamicPreprocessor = None
    self.model_if: IsolationForest = None
    self.model_rf: RandomForestClassifier = None
    
    self.last_model_version_time = 0
    
    self.ISOLATIONFOREST_MODEL_PATH = f"models/{self.target_table}_if_model.pkl"
    self.RANDOMFOREST_MODEL_PATH = f"models/{self.target_table}_rf_model.pkl"

  def start_detection(self) -> None:
    self._register_pipeline()
    
    if not self._load_models():
      return
    KAFKA_TOPIC = f"source-postgres.public.{self.target_table}"

    
    logging.info(f"Worker started for the {self.target_table} pipeline.")

    for event_json in consumer_kafka_stream(
      topic=KAFKA_TOPIC,
      group_id=self.group_id
    ):
      try:
        if os.path.exists(self.RANDOMFOREST_MODEL_PATH):
          current_file_time = os.path.getmtime(self.RANDOMFOREST_MODEL_PATH)
            
          if current_file_time > self.last_model_version_time:
            logging.warning("New model detected, reloading...")
            self._load_models()
            logging.warning("Reload complete")
          
        logging.info(f"Stream received from Kafka! Processing payload ID: {event_json.get('id', 'Unknown')}")
        features = self.preprocessor.transform_json_to_features(event_json)
          
        score_if = self.model_if.decision_function(features)[0]
          
        # Only get the probability if the RF model was loaded
        prob_rf = None
        if self.model_rf:
          prob_rf = self.model_rf.predict_proba(features)[0][1]
          
        is_anomaly = self._judge_prediction(score_if=score_if, prob_rf=prob_rf)
          

        if is_anomaly == True:
          logging.info("Anomaly detected, sending to kafka")

          for col in self.date_columns:
            date_value = event_json.get(col)
            if date_value and isinstance(date_value, int):
              # Converting microseconds to date 
              dt = datetime.fromtimestamp(date_value / 1_000_000.0, tz=timezone.utc)
              event_json[col] = dt.strftime('%d/%m/%Y %H:%M:%S')

          model_used = "Hybrid (RF+IF)" if prob_rf is not None else "IsolationForest_v1"

          payload_anomaly = {
            "id": f"ALRT-{event_json.get('id', 'N/A')}",
            "timestamp_detection": datetime.now(timezone.utc).isoformat(),
            "origin": {
                "table": self.target_table,
                "source_topic": KAFKA_TOPIC
            },
            "ml_model": model_used,
            "status": "pending_revision",
            "raw_event": event_json 
          }
          
          self.anomaly_producer.send_anomaly(
            topic="detected_anomalies", 
            payload=payload_anomaly
          )

      except Exception as e:
        logging.error(f"An unexpected error occured while predicting the features: {e}")
      
  def _judge_prediction(self,score_if:float,prob_rf:float = None) -> bool:
    """This is the implementation of a hybrid ML model, that uses IsolationForest to discover new anomlies patterns,
    and simultaneosly uses RandomForestClassifier to increase the prediction accuracy of known anomalies

    Args:
        score_if (float): Score predicted by IsolationForest
        score_rf (float): Score predicted by RandomForest

    Returns:
        bool: True = The event is an anomaly
    """
    if prob_rf is not None:
      #If Random forest has more than 85% sure, the event is an anomaly
      if prob_rf > 0.85:
        return True
      
      #If Random forest was not so sure on the event, but Isolation forest thought it was a weird event,then is an anomaly
      if prob_rf > 0.4 and score_if < -0.15:
        return True
    
    if score_if < -0.1:
      return True
      
    return False
  
  def _load_models(self):
    """Loads all available models and preprocessor at startup."""
    
    # --- Load Isolation Forest (Mandatory) ---
    try:
      logging.info("Loading Unsupervised Model (Isolation Forest)...")
      self.preprocessor = DynamicPreprocessor(
        table_name=self.target_table,
        columns_to_ignore=self.columns_to_ignore
      )
      self.model_if = joblib.load(self.ISOLATIONFOREST_MODEL_PATH)
    except FileNotFoundError:
      logging.error(f"Isolation Forest model not found at {self.ISOLATIONFOREST_MODEL_PATH}. Worker cannot start.")
      return False
      
    try:
      if os.path.exists(self.RANDOMFOREST_MODEL_PATH):
        logging.info("Loading Supervised Model (Random Forest)...")
        self.model_rf = joblib.load(self.RANDOMFOREST_MODEL_PATH)
      else:
        logging.warning("Random Forest model not found. Running in Unsupervised-Only mode.")
    except Exception as e:
      logging.error(f"Failed to load Random Forest model, will proceed without it. Error: {e}")
      self.model_rf = None
      
    if os.path.exists(self.RANDOMFOREST_MODEL_PATH):
      self.last_model_version_time = os.path.getmtime(self.RANDOMFOREST_MODEL_PATH)

    return True
        
  def _register_pipeline(self):
    """The worker creates a registration for itself, so the anomalies hub can check its data"""
      
    engine = get_db_engine()

    create_table_query = text("""
      CREATE TABLE IF NOT EXISTS pipelines_config (
        target_table VARCHAR(100) PRIMARY KEY,
        pipeline_name VARCHAR(100),
        columns_to_ignore TEXT,
        date_columns TEXT,
        status VARCHAR(20) DEFAULT 'active',
        last_startup TIMESTAMP
      );
    """)

    cols_ignore_str = ",".join(self.columns_to_ignore) if self.columns_to_ignore else ""
    dates_str = ",".join(self.date_columns) if self.date_columns else ""
      
    nome_bonito = f"Worker de {self.target_table.replace('_', ' ').title()}"

    upsert_query = text("""
      INSERT INTO pipelines_config (target_table, pipeline_name, columns_to_ignore, date_columns, last_startup)
      VALUES (:target, :name, :cols, :dates, CURRENT_TIMESTAMP)
      ON CONFLICT (target_table)
      DO UPDATE SET 
        columns_to_ignore = EXCLUDED.columns_to_ignore,
        date_columns = EXCLUDED.date_columns,
        last_startup = EXCLUDED.last_startup,
        status = 'active';
    """)

    try:
      with engine.connect() as conn:
        conn.execute(create_table_query)
        conn.execute(upsert_query, {
          "target": self.target_table,
          "name": nome_bonito,
          "cols": cols_ignore_str,
          "dates": dates_str
        })
        conn.commit()
        logging.info(f"Pipeline {self.target_table} inserted in anomalies hub")
    except Exception as e:
      logging.error(f"Error registering the pipeline at anomalies Hub: {e}")