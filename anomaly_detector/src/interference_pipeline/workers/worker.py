import logging
from typing import List
import joblib
from interference_pipeline.preprocessing_data.preprocess_data import DynamicPreprocessor
from interference_pipeline.consumer.consumer import consumer_kafka_stream
from interference_pipeline.producer.producer import AnomalyProducer
from sklearn.ensemble import IsolationForest
from datetime import datetime, timezone


class Worker:

  def __init__(self,target_table:str,group_id:str,columns_to_ignore: List[str],date_columns:List[str] = None):
    self.target_table = target_table

    self.group_id = group_id
    self.columns_to_ignore = columns_to_ignore or ['id'] 
    self.date_columns = date_columns or []
    self.anomaly_producer = AnomalyProducer()

  def start_detection(self) -> None:
    MODEL_PATH = f"models/{self.target_table}_model.pkl"
    KAFKA_TOPIC = f"source-postgres.public.{self.target_table}"

    #Instantiating the preprocessor and the ML model
    preprocessor = DynamicPreprocessor(
      table_name=self.target_table,
      columns_to_ignore=self.columns_to_ignore
    )

    try:
      ml_model: IsolationForest = joblib.load(MODEL_PATH)

      logging.info(f"Worker started for the {self.target_table} pipeline.")

      for event_json in consumer_kafka_stream(
        topic=KAFKA_TOPIC,
        group_id=self.group_id
      ):
        logging.info(f"Stream received from Kafka! Processing payload ID: {event_json.get('id', 'Unknown')}")

        features = preprocessor.transform_json_to_features(event_json)

        prediction = ml_model.predict(features)

        if prediction[0] == -1:
          logging.info("Anomaly detected, sending to kafka")

          for col in self.date_columns:
              date_value = event_json.get(col)
              if date_value and isinstance(date_value, int):
                  # Converting microseconds to date 
                  dt = datetime.fromtimestamp(date_value / 1_000_000.0, tz=timezone.utc)
                  event_json[col] = dt.strftime('%d/%m/%Y %H:%M:%S')

          payload_anomaly = {
            "id": f"ALRT-{event_json.get('id', 'N/A')}",
            "timestamp_detection": datetime.now(timezone.utc).isoformat(),
            "origin": {
                "table": self.target_table,
                "source_topic": KAFKA_TOPIC
            },
            "ml_model": "IsolationForest_v1",
            "status": "pending_revision",
            "raw_event": event_json 
          }

          self.anomaly_producer.send_anomaly(
            topic="detected_anomalies", 
            payload=payload_anomaly
          )

    except Exception as e:
      logging.error(f"An unexpected error occured while predicting the features: {e}")