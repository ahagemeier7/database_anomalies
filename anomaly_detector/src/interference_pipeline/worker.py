import os
import logging
from typing import List
import joblib
from interference_pipeline.preprocessing_data.preprocess_data import DynamicPreprocessor
from interference_pipeline.consumer.consumer import consumer_kafka_stream
from interference_pipeline.producer.producer import AnomalyProducer
from sklearn.ensemble import IsolationForest,RandomForestClassifier
from datetime import datetime, timezone


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

  def start_detection(self) -> None:
    if not self._load_models():
      return
    KAFKA_TOPIC = f"source-postgres.public.{self.target_table}"

    try:
      logging.info(f"Worker started for the {self.target_table} pipeline.")

      for event_json in consumer_kafka_stream(
        topic=KAFKA_TOPIC,
        group_id=self.group_id
      ):
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
    and simultaneosly uses RandomForestClassifier to increse the prediction accuracy of known anomalies

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
    
    ISOLATIONFOREST_MODEL_PATH = f"models/{self.target_table}_if_model.pkl"
    RANDOMFOREST_MODEL_PATH = f"models/{self.target_table}_rf_model.pkl"

    # --- Load Isolation Forest (Mandatory) ---
    try:
      logging.info("Loading Unsupervised Model (Isolation Forest)...")
      # Assuming one preprocessor is enough if features are the same
      self.preprocessor = DynamicPreprocessor(
        table_name=self.target_table,
        columns_to_ignore=self.columns_to_ignore
      )
      self.model_if = joblib.load(ISOLATIONFOREST_MODEL_PATH)
    except FileNotFoundError:
      logging.error(f"Isolation Forest model not found at {ISOLATIONFOREST_MODEL_PATH}. Worker cannot start.")
      return False
      
    try:
      if os.path.exists(RANDOMFOREST_MODEL_PATH):
        logging.info("Loading Supervised Model (Random Forest)...")
        self.model_rf = joblib.load(RANDOMFOREST_MODEL_PATH)
      else:
        logging.warning("Random Forest model not found. Running in Unsupervised-Only mode.")
    except Exception as e:
      logging.error(f"Failed to load Random Forest model, will proceed without it. Error: {e}")
      self.model_rf = None
        
    return True