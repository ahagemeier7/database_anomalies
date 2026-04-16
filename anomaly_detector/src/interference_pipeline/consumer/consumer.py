import os
import json
import logging
from confluent_kafka import Consumer, KafkaError


def consumer_kafka_stream(topic: str,group_id: str):

  bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')

  conf = {
    'bootstrap.servers' : bootstrap_servers,
    'group.id': group_id,     
    'auto.offset.reset': 'latest',
    'allow.auto.create.topics': True
  }

  consumer = Consumer(conf)

  consumer.subscribe([topic])

  print(f"Conected to kafka, listenin on topic: {topic}...")

  try:
    while True:
      msg = consumer.poll(timeout=1.0)

      if msg is None:
        continue
    
      if msg.error():
        if msg.error().code() in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
          continue 
        else:
          print(f"Error: {msg.error()}")
          break
    
      valor_byte = msg.value()

      if valor_byte:
        data = json.loads(valor_byte.decode('utf-8'))

        operation = data.get('op')

        if operation in ['c','r']:
          new_registry = data.get('after')

          yield new_registry
  except Exception as e:
    logging.error(f"An unexpected error occured while listening to kafka stream: {e}")
  except KeyboardInterrupt:
    logging.warning("Shutting down the pipeline by user request")
  finally:
    consumer.close()