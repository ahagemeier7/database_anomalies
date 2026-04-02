import os
import json
import logging
from confluent_kafka import Producer

def delivery_report(err,msg):
  if err is not None:
    logging.error(f"Failed to send the message to kafka: {err}")
  else:
    logging.debug(f"Anomaly sent to topic {msg.topic()}")

def producer_kafka_stream(topic:str,payload:dict):
  """
  Send the detected anomaly back to kafka
  """
  try:
    kafka_server = os.getenv('KAFKA_BOOTSTRAP_SERVER')

    producer = Producer({'bootstrap.servers': kafka_server})

    message_bytes = json.dumps(payload).encode('utf-8')

    producer.produce(
      topic=topic,
      value=message_bytes,
      callback=delivery_report
    )

    producer.flush()
  except Exception as e:
    logging.error("Faild to produce the kafka message")

