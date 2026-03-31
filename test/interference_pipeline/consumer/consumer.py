import os
import json
from confluent_kafka import Consumer, KafkaError


def consumer_kafka_stream(topico: str,group_id: str):

  bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVER')

  conf = {
    'bootstrap.servers' : bootstrap_servers,
    'group.id': group_id,     
    'auto.offset.reset': 'latest' 
  }

  consumer = Consumer(conf)


  consumer.subscribe([topico])

  print(f"Conectado ao Kafka! Escutando novos registros no tópico: {topico}...")
  print("Faça um INSERT no banco de dados para testar.\n")


  try:
    while True:
      msg = consumer.poll(timeout=1.0)

      if msg is None:
        continue
    
      if msg.error():
        if msg.error().code() == KafkaError._PARTITION_EOF:
          continue # Fim da fila, normal.
        else:
          print(f"Erro no Kafka: {msg.error()}")
          break
    
      valor_byte = msg.value()

      if valor_byte:
        dados = json.loads(valor_byte.decode('utf-8'))

        operacao = dados.get('op')

        if operacao in ['c','r']:
          registro_novo = dados.get('after')

          yield registro_novo

  except KeyboardInterrupt:
    print("Encerrando escuta")
  finally:
    consumer.close()