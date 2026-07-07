# Base source database connector

Este conector é criado automaticamente pelo compose quando o ambiente sobe, através do serviço kafka-connect-setup. Ele faz o CDC da tabela insurance_claims e publica os eventos no tópico source-postgres.public.insurance_claims para que o detector consuma as fraudes.

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
  "table.include.list": "public.insurance_claims",
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter.schemas.enable": "false",
  "decimal.handling.mode": "double",
  "snapshot.mode": "initial"
}