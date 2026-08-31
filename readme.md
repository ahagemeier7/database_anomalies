# Hub de detecção de anomalias
Projeto de estudo sobre detecção de anomalias com Machine Learning, streaming e processamento orientado a eventos.

## Descrição
<<<<<<< HEAD
Este projeto foi criado para estudar arquitetura de software, machine learning e engenharia de dados. Ele implementa uma pipeline de detecção de anomalias para tabelas de banco de dados, com foco em demonstração acadêmica e revisão humana dos alertas.
O cenário padrão conta com 11 serviços em containers, sendo:
- 2 deles para a aplicação web que contém um hub de detecção de anomalias
- 2 para a detecção e tratamento das anomalias encontradas
- 2 para banco de dados em postgres (sendo um para a aplicação e outro simulando o banco de origem dos dados)
- 5 para CDC, streaming e observabilidade: Zookeeper, Kafka, Kafka Connect, configuração automática do conector e Kafka UI

## Dataset
- [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) (dataset ativo na demonstração)
  - Informações de transações feitas por cartões de crédito durante dois dias. Existem 492 fraudes e 284807 transações.
=======
Esse projeto foi criado para estudar arquitetura de software, Machine Learning e engenharia de dados. A pipeline captura alterações em uma tabela PostgreSQL, publica eventos no Kafka, aplica modelos de detecção e disponibiliza os alertas em um hub web para revisão.
O Compose possui 11 serviços principais e um serviço opcional de seed, sendo:
- 2 deles para a aplicação web que contém um hub de detecção de anomalias
- 2 para a detecção e tratamento das anomalias encontradas
- 2 para banco de dados em postgres (sendo um para a aplicação e outro simulando o banco de origem dos dados)
  - 5 para streaming, replicação, monitoramento e configuração do ambiente

## Dataset
- [https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud] (Utilizado durante o desenvolvimento)
  - O dataset original possui 284807 transações e 492 fraudes. A demonstração local usa o arquivo reduzido `creditcard_small.csv`, com 15492 registros, incluindo as 492 fraudes.
>>>>>>> 51ac7d987670aa2e84b89c8e7be07652e5159fef

- [Vehicle Claim Fraud Detection](https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection)
  - Dataset experimental de seguros mantido nos scripts; não faz parte do fluxo padrão do Compose.

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
    - O detector publica as anomalias em um tópico Kafka
    - O handler persiste os alertas no banco interno e pode enviar um aviso por email

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
- Debezium Connect: 3.2
- Kafka UI: v0.7.2
- Python dependencies: ver `requirements.txt` de cada módulo

<<<<<<< HEAD
**Nota**: O projeto roda totalmente em containers; não é necessário iniciar backend ou frontend localmente se usar `docker compose up`.
=======
**Nota**: O projeto roda totalmente em containers; não é necessário iniciar backend ou frontend localmente quando o Compose é usado.
>>>>>>> 51ac7d987670aa2e84b89c8e7be07652e5159fef

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
O envio de email é opcional. Para habilitá-lo, configure as variáveis no `.env` usando uma senha de aplicativo, sem versionar credenciais:
- `SENDER_EMAIL`: endereço configurado somente localmente
- `EMAIL_PASSWORD`: senha de aplicativo configurada somente localmente
- `RECIEVER_EMAIL`: destinatário configurado somente localmente

## Instalação e Execução

### Configuração do ambiente

O `docker-compose.yml` contém a configuração de demonstração diretamente no arquivo. O `.env.example` é uma referência dos valores do cenário de cartão e não é consumido pelo Compose nesta versão. Para evitar envio acidental de dados pessoais, não versione um `.env` local.

### Opção 1: Com Docker Compose (Recomendado)
```bash
# Depois de clonar o repositório, entre na pasta do projeto
cd database_anomalies

# Iniciar todos os serviços
docker compose up --build

# Em outro terminal, para ver logs
docker compose logs -f

# Parar os serviços
docker compose down
```

### Opção 2: Com seed de dados
```bash
<<<<<<< HEAD
# Iniciar os serviços e o seed de dados
=======
# Copiar o template de ambiente
cp .env.example .env

# Iniciar os serviços e executar o seed de dados do dataset de cartão
>>>>>>> 51ac7d987670aa2e84b89c8e7be07652e5159fef
docker compose --profile seed up --build -d
```

### Como verificar se tudo subiu
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Kafka UI: `http://localhost:8080`
- Kafka Connect: `http://localhost:8083`

### Demonstração com dados

O serviço `seed_transactions` é executado somente com o profile `seed`. Ele insere os registros normais, aguarda o treinamento inicial da pipeline `creditcard_transactions` e depois insere os registros fraudulentos:

```bash
docker compose up --build -d
docker compose --profile seed up --build seed_transactions
```

Depois, consulte o dashboard em `http://localhost:3000` ou a API em `http://localhost:8000/api/anomalies`.

## Estrutura do projeto
- anomalies_hub_backend - Backend da aplicação web, feito com python e FastAPI
- anomalies_hub_frontend - Frontend da aplicação. Feito com React + Vite
- anomaly_detector - Analisa os eventos do kafka para detectar anomalias. Python + Scikit-Learn
- anomaly_handler - Trata as anomalias, persistindo-as no banco interno e podendo enviar um aviso por email
- docs - Contém o diagrama da arquitetura e a configuração base para o conector source do kafka
- scripts
  - model_testing - Validação das configurações dos modelos de ML, e testes de modelo híbrido
  - startup_datasets_seed - Contém arquivos para o seed inicial com os dados do dataset

## Fluxo dos dados
Banco de dados origem (cdc) -> debezium -> Kafka -> anomaly detector -> kafka -> anomaly handler -> Banco de dados interno (Postgres) -> anomalies hub backend -> anomalies hub frontend

## Roteiro de demonstração

1. Execute `docker compose --profile seed up --build -d`.
2. Confirme no Kafka Connect (`http://localhost:8083/connectors/source-postgres/status`) que o conector está em execução.
3. Abra o Kafka UI (`http://localhost:8080`) para observar o tópico `source-postgres.public.creditcard_transactions` e, quando houver alerta, `detected_anomalies`.
4. Abra o Hub (`http://localhost:3000`) e revise os alertas pendentes. Marque um como fraude confirmada ou falso positivo.
5. Após registrar ao menos uma fraude confirmada e um falso positivo, acione o retreinamento pelo Hub ou por `POST /api/pipelines/creditcard_transactions/retrain`; a nova versão registra métricas supervisionadas.
6. Para usar os dois modelos, selecione o modo `hybrid` no Hub depois do retreinamento. A API equivalente é `POST /api/pipelines/creditcard_transactions/inference-mode` com `{ "inference_mode": "hybrid" }`; a pipeline inicia em `if` enquanto não há modelo supervisionado válido.

Este é um MVP acadêmico. As credenciais do Compose são locais, os resultados não representam validação para produção e cada alerta deve passar por revisão humana.

## Comandos úteis

### Docker
```bash
# Ver logs de um serviço específico
docker compose logs -f hub-backend
docker compose logs -f worker-worker_transactions

# Listar containers e status
docker compose ps

# Reiniciar um serviço
docker compose restart hub-backend

# Parar todos os serviços e remover volumes (limpeza total)
docker compose down -v

# Rebuildar uma imagem após mudanças
docker compose build hub-backend
```

### Desenvolvimento
```bash
# Subir tudo em foreground (com logs)
docker compose up

# Subir tudo em background
docker compose up -d

# Subir apenas serviços específicos
docker compose up hub-backend hub-frontend

# Rebuildar e subir (após alterações de código)
docker compose up --build
```

## API Reference

A documentação interativa da API (Swagger UI) está disponível em:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Endpoints

#### Anomalias

| Método | Path | Descrição |
|--------|------|-----------|
| `GET` | `/api/anomalies` | Lista anomalias paginadas. Query params: `status` (default: `pending_revision`), `limit`, `offset`, `origin_table` |
| `PUT` | `/api/anomalies/{alert_id}/status` | Atualiza o status de um alerta. Body: `{ "status": "confirmed_fraud" \| "false_positive" \| "pending_revision" }` |
| `GET` | `/api/anomalies/stats` | Retorna contagens por status, gráfico dos últimos 7 dias e precision baseada nos alertas revisados |
| `GET` | `/api/anomalies/stats/by-table` | Retorna contagens agrupadas por tabela e precision baseada nos alertas revisados |

#### Pipelines

| Método | Path | Descrição |
|--------|------|-----------|
| `GET` | `/api/pipelines` | Lista todas as pipelines de ML configuradas, com contagem de pendentes |
| `POST` | `/api/pipelines/{target_table}/retrain` | Executa o retreinamento dos modelos para a tabela alvo |

### Métricas exibidas no dashboard

O dashboard exibe:

- total de alertas;
- alertas pendentes;
- fraudes confirmadas;
- falsos positivos;
- histórico diário de fraudes confirmadas e falsos positivos;
- precision global e por tabela.

Os números de fraudes confirmadas e falsos positivos vêm do status atribuído durante a revisão dos alertas. A precision exibida é calculada assim:

`fraudes confirmadas / (fraudes confirmadas + falsos positivos)`

Essa é uma métrica operacional da revisão dos alertas, não uma avaliação completa do modelo. Recall, F1-score e matriz de confusão ainda precisam ser calculados em um conjunto de teste rotulado antes de serem divulgados como métricas de desempenho do Machine Learning.

## Troubleshooting

### Porta 3000 já está em uso
```bash
# Linux/macOS
lsof -i :3000

# Windows
netstat -ano | findstr :3000
```
Encerre o processo que está usando a porta ou altere a porta no `docker-compose.yml`.

### Modelo não treina
- Verifique permissões da pasta `anomaly_detector/src/models` — precisa ser gravável
<<<<<<< HEAD
- Confira se os dados de seed estão disponíveis: `docker compose logs seed_transactions`
=======
- Confira se os dados de seed estão disponíveis: `docker compose --profile seed logs seed_transactions`
>>>>>>> 51ac7d987670aa2e84b89c8e7be07652e5159fef
- Se a tabela não existir no source-DB, a pipeline não encontrará dados para treinar

### Kafka não conecta
```bash
# Verificar logs do Kafka
docker compose logs kafka

# Verificar se o Zookeeper está saudável
docker compose logs zookeeper
```
Aguarde ~30 segundos após `docker compose up` para o Kafka inicializar completamente.

### Erro de conexão no backend
- Confirme que o banco interno está rodando: `docker compose logs postgres-internal`
- Verifique as variáveis de ambiente no `docker-compose.yml` (seção `hub-backend`)
- O backend depende do `postgres-internal` — certifique-se de que ele está healthy

## Melhorias e sugestões
- [x] Cobertura inicial de testes (pytest)
- [ ] CI/CD com GitHub Actions
- [ ] Logs estruturados em JSON
- [ ] Health checks nos containers
- [ ] Otimização multi-stage dos Dockerfiles

Sugestões são bem-vindas! Abra uma issue ou envie um PR.
