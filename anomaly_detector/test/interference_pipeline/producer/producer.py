import os
import json
import logging
from confluent_kafka import Producer

def delivery_report(err,msg):
  if err is not None:
    logging.error(f"Failed to send the message to kafka: {err}")
  else:
    logging.debug(f"Anomaly sent to topic {msg.topic()}")

class AnomalyProducer:
  """
  Class that keeps an open connection with kafka to send the anomaly messages
  """
  def __init__(self):
    self.kafka_server = os.getenv('KAFKA_BOOTSTRAP_SERVERS')

    self.producer = Producer({'bootstrap.servers': self.kafka_server}) 

  def send_anomaly(self,topic:str,payload:dict):
    try:

      message_bytes = json.dumps(payload).encode('utf-8')

      self.producer.produce(
        topic=topic,
        value=message_bytes,
        callback=delivery_report
      )

      self.producer.flush()
    except Exception as e:
      logging.error("Faild to produce the kafka message")
