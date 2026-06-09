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
- Docker e Docker Compose para orquestrar os serviços de Kafka, PostgreSQL, Debezium e o aplicativo
- O projeto roda totalmente em containers; não é necessário iniciar backend ou frontend localmente

## Instalação e execução
- Inicie os containers: `docker-compose up` na raiz do projeto
- Aguarde até que todos os serviços estejam prontos e acesse a aplicação pelo endereço configurado no frontend/hub-frontend
- Para parar os serviços: `docker-compose down`