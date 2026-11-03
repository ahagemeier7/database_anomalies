import os
import json
import logging
from confluent_kafka import Consumer, KafkaError


def consumer_kafka_stream(topic: str,group_id: str):

  bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')

  conf = {
    'bootstrap.servers' : bootstrap_servers,
    'group.id': group_id,
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'enable.auto.offset.store': False,
    'allow.auto.create.topics': True
  }

  consumer = Consumer(conf)

  consumer.subscribe([topic])

  logging.info(f"Connected to Kafka, listening on topic: {topic}...")

  try:
    while True:
      msg = consumer.poll(timeout=1.0)

      if msg is None:
        continue
    
      if msg.error():
        if msg.error().code() in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
          continue 
        else:
          raise RuntimeError(f"Kafka error: {msg.error()}")
    
      valor_byte = msg.value()

      if valor_byte:
        data = json.loads(valor_byte.decode('utf-8'))

        operation = data.get('op')

        if operation in ['c', 'r']:
          new_registry = data.get('after')
          if isinstance(new_registry, dict):
            yield new_registry
      # Resuming iteration means the caller completed processing. A failure
      # or close while handling a record never reaches this acknowledgment.
      consumer.commit(message=msg, asynchronous=False)
  except Exception as e:
    logging.exception("Kafka consumption failed; leaving the record uncommitted")
    raise
  except KeyboardInterrupt:
    logging.warning("Shutting down the pipeline by user request")
  finally:
    consumer.close()
