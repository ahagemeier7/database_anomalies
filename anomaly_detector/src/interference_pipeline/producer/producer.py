import os
import json
from confluent_kafka import Producer

class AnomalyProducer:
  """
  Class that keeps an open connection with kafka to send the anomaly messages
  """
  def __init__(self):
    self.kafka_server = os.getenv('KAFKA_BOOTSTRAP_SERVERS')

    self.producer = Producer({
      'bootstrap.servers': self.kafka_server,
      'enable.idempotence': True,
      'delivery.timeout.ms': 10000,
    })

  def send_anomaly(self,topic:str,payload:dict):
    failures = []

    def delivered(error, message):
      if error is not None:
        failures.append(str(error))

    self.producer.produce(
      topic=topic,
      value=json.dumps(payload).encode('utf-8'),
      callback=delivered,
    )
    if self.producer.flush(10) != 0:
      raise TimeoutError('Kafka delivery was not confirmed within 10 seconds')
    if failures:
      raise RuntimeError(f'Kafka delivery failed: {failures[0]}')
