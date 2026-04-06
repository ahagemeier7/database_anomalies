import os
import logging
import json
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError

load_dotenv()

def anomaly_consumer_kafka(topic:str,group_id:str):

  bootstrap_server = os.getenv("KAFKA_BOOTSTRAP_SERVER")

  conf = {
    'bootstrap.servers' : bootstrap_server,
    'group.id': group_id,     
    'auto.offset.reset': 'latest' 
  }

  consumer = Consumer(conf)

  consumer.subscribe(topics=topic)

  try:
    while True:
      msg = consumer.poll(timeout=1.0)

      if msg is None:
        continue

      if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
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
