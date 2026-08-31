# Base source database connector

Este conector é criado automaticamente pelo Compose quando o ambiente sobe, através do serviço `kafka-connect-setup`. Ele faz CDC da tabela `creditcard_transactions` e publica os eventos no tópico `source-postgres.public.creditcard_transactions`, consumido pelo detector.

Connector name: source-postgres
{
  "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
  "plugin.name": "pgoutput",
  "database.hostname": "postgres-source",
  "database.port": "5432",
  "database.user": "postgres",
  "database.password": "postgres",
  "database.dbname": "db_real",
  "topic.prefix": "source-postgres",
  "table.include.list": "public.creditcard_transactions",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter.schemas.enable": "false",
  "decimal.handling.mode": "double",
  "snapshot.mode": "initial"
}
