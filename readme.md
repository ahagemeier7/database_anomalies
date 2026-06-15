# Hub de detecção de anomalias
Projeto de estudo sobre detecção de anomalias com machine learning

## Descrição
Esse projeto foi criado para entender conceitos de arquitetura de software, machine learning e engenharia de dados. Para isso, foi desenvolvido uma pipeline de detecção de anomalias para diferentes tabelas de banco de dados de maneira, simples, eficiente e de boa confiabilidade.
O projeto conta com 10 containers trabalhando em conjunto, sendo:
- 2 deles para a aplicação web que contém um hub de detecção de anomalias
- 2 para a detecção e tratamento das anomalias encontradas
- 2 para banco de dados em postgres (sendo um para a aplicação e outro simulando o banco de origem dos dados)
- 4 para rodar os serviços de replicação do banco de origem para a aplicação

## Dataset
- [https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud] (Utilizado durante o desenvolvimento)
  - Informações de transações feitas por cartões de crédito durante dois dias. Existem 492 fraudes e 284807 transações.

- [https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection]
  - Informações de indenizações de seguros, contendo informações dos carros, do acidente e do condutor

## Arquitetura do projeto
 - Fonte de dados
    - Um banco de dados de origem (Source DB)
    - O Debezium faz CDC (Change Data Capture) e publica os eventos de mudança no Kafka

  - Plataforma de streaming
    - Kafka é a camada de mensageria
    - Zookeeper gerencia o cluster Kafka
    - Kafka UI é usada para monitorar tópicos e mensagens

  - Serviços de processamento
    - Anomaly Detector consome os eventos do Kafka, aplica o modelo de detecção e identifica anomalias
    - Anomaly Handler também consome do Kafka e faz o tratamento das anomalias geradas
    - O detector envia as anomalias para a aplicação web / banco interno

  - Aplicação web
    - Frontend em React/Vite
    - Backend API em Python
    - Banco de dados interno PostgreSQL para armazenar os resultados e o status das anomalias

## Requisitos

### Sistema
- **Docker**: versão 20.10+ 
- **Docker Compose**: versão 2.0+
- **RAM**: mínimo 4GB disponível (recomendado 8GB)
- **Espaço em disco**: mínimo 5GB

### Versões dos componentes principais
- Kafka: 7.4.0
- PostgreSQL: 15-alpine
- Zookeeper: 7.4.0 (integrado com Kafka)
- Debezium: latest
- Python dependencies: ver `requirements.txt` de cada módulo

**Nota**: O projeto roda totalmente em containers; não é necessário iniciar backend ou frontend localmente se usar `docker-compose up`

## Credenciais e Portas Padrão

### Serviços Web
| Serviço | URL | Descrição |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | Aplicação web de detecção de anomalias |
| Backend API | http://localhost:8000 | API FastAPI |
| Kafka UI | http://localhost:8080 | Monitoramento de tópicos Kafka |
| Kafka Connect | http://localhost:8083 | Gerenciamento de conectores Debezium |
| Kafka | localhost:9092 | Broker Kafka |
| Zookeeper | localhost:2181 | Orquestrador Kafka |

### Email (Anomaly Handler)
**⚠️ Configurar antes de usar o handler:**
- `SENDER_EMAIL`: seu_email@gmail.com (seu Gmail)
- `EMAIL_PASSWORD`: sua_senha_de_app (senha de app do Gmail)
- `RECIEVER_EMAIL`: equipe_fraude@empresa.com (destinatário)

## Instalação e Execução

### Opção 1: Com Docker Compose (Recomendado)
```bash
# Clonar o repositório
git clone <seu-repositorio>
cd database_anomalies

# Iniciar todos os serviços
docker-compose up

# Em outro terminal, para ver logs
docker-compose logs -f

# Parar os serviços
docker-compose down
```

## Estrutura do projeto
- anomalies_hub_backend - Backend da aplicação web, feito com python e FastAPI
- anomalies_hub_frontend - Frontend da aplicação. Feito com React + Vite
- anomaly_detector - Analisa os eventos do kafka para detectar anomalias. Python + Scikit-Learn
- anomaly_handler - Trata as anomalias, enviando elas para o banco interno e um aviso por email
- docs - Contém o diagrama da arquitetura e a configuração base para o conector source do kafka
- scripts
  - model_testing - Validação das configurações dos modelos de ML, e testes de modelo híbrido
  - startup_datasets_seed - Contém arquivos para o seed inicial com os dados do dataset

## Fluxo dos dados
Banco de dados origem (cdc) -> debezium -> Kafka -> anomaly detector -> kafka -> anomaly handler -> Banco de dados interno (Postgres) -> anomalies hub backend -> anomalies hub frontend

## Comandos úteis


## Melhorias e sugestões
