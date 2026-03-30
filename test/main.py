import json
from confluent_kafka import Consumer, KafkaError

conf = {
  'bootstrap.servers' : 'localhost:9092',
  'group.id': 'teste_conexao',     
  'auto.offset.reset': 'latest' 
}

consumer = Consumer(conf)

TOPICO = 'source-postgres.public.clientes'

consumer.subscribe([TOPICO])

print(f"Conectado ao Kafka! Escutando novos registros no tópico: {TOPICO}...")
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

        print("="*50)
        print("Novo registro no banco!")
        print(json.dumps(registro_novo,indent=4,ensure_ascii=False))
        print("="*50 + "\n")

except KeyboardInterrupt:
  print("Encerrando escuta")
finally:
  consumer.close()
