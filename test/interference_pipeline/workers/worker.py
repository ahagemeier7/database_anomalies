import logging
from typing import List
import joblib
from preprocessing_data.preprocess_data import DynamicPreprocessor
from consumer.consumer import consumer_kafka_stream
from producer.producer import producer_kafka_stream
from sklearn.ensemble import IsolationForest
from datetime import datetime, timezone


class Worker:

  def __init__(self,target_table:str,group_id:str,columns_to_ignore: List[str]):
    self.target_table = target_table

    self.group_id = group_id
    self.columns_to_ignore = columns_to_ignore or ['id'] 

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
        topico=KAFKA_TOPIC,
        group_id=self.group_id
      ):

        features = preprocessor.transform_json_to_features(event_json)

        prediction = ml_model.predict(features)

        if prediction[0] == -1:
          logging.info("Anomaly detected, sending to kafka")

          payload_anomaly = {
            "id_alerta": f"ALRT-{event_json.get('id', 'N/A')}",
            "timestamp_deteccao": datetime.now(timezone.utc).isoformat(),
            "origem": {
                "tabela": self.target_table,
                "topico_fonte": KAFKA_TOPIC
            },
            "modelo_ml": "IsolationForest_v1",
            "status": "pendente_revisao",
            "evento_bruto": event_json 
          }

          producer_kafka_stream(topic="detected_anomalies",payload=payload_anomaly)

    except Exception as e:
      logging.error(f"An unexpected error occured while predicting the features: {e}")