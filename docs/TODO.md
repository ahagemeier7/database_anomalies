# TODO — Correções e Melhorias para o FraudOps

Lista do que falta ajustar. Ordenado por prioridade.

---

## 🔴  Ainda pendente

### 1. ✅ `print()` em produção no consumer do anomaly_handler -- CORRIGIDO

**Arquivo:** `anomaly_handler/src/consumer/consumer.py` — linha 35

**Problema:** `print(f"Error: {msg.error()}")` — stdout não tem timestamp, nível, nem formato estruturado.

```python
# CORRIGIR:
logging.error(f"Kafka error: {msg.error()}")
```

---

### 2. ✅ CORS inválido no backend -- CORRIGIDO

**Arquivo:** `anomalies_hub_backend/main.py` — linhas 17-18

**Problema:** `allow_credentials=True` combinado com `allow_origins=["*"]` é ilegal na especificação CORS. Navegadores rejeitam essa combinação.

```python
# CORRIGIR:
allow_origins=["http://localhost:3000"],
allow_credentials=False,
```

---

## 🟡 Polimento

### 3. Link do dashboard no email é placeholder

**Arquivo:** `anomaly_handler/src/handler/handler.py` — linha 116

**Problema:** O botão "Review in Dashboard" tem `href="#"`.

```python
dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
```

---

### 4. ✅ Versões de Python inconsistentes nos Dockerfiles -- CORRIGIDO

- `anomaly_detector/Dockerfile` — `python:3.10-slim`
- `anomaly_handler/Dockerfile` — `python:3.10-slim`
- `anomalies_hub_backend/Dockerfile` — `python:3.12-slim`

Padronizar tudo para `python:3.12-slim`.

---

### 5. Senhas hardcoded nos scripts de seed

**Arquivos:** `scripts/seed_anomalies.py` (linhas 23-24) e `fake_datasets_seed/dataset_seed.py` (linha 7)

Ler de `.env` com fallback local.

---

### 6. Sem `.dockerignore` em nenhum serviço

Criar em cada serviço:
```
__pycache__
.venv
*.pyc
*.csv
*.pkl
models/
.git
```

---

### 7. Typos espalhados

| Arquivo | Erro | Correção |
|---------|------|----------|
| `anomaly_detector/main.py` | `occured` | `occurred` |
| `anomaly_handler/main.py` | `occured` | `occurred` |
| `anomaly_detector/.../consumer.py` | `occured` | `occurred` |
| `anomaly_handler/.../consumer.py` | `occured` | `occurred` |
| `anomaly_detector/.../producer.py` | `Faild` | `Failed` |
| `anomaly_handler/.../db.py` | `databese` | `database` |
| `anomaly_detector/.../worker_models_retraining.py` | `iternal` | `internal` |
| `anomaly_handler/.../handler.py` | `reciever` | `receiver` |
| `anomaly_detector/.../worker.py` | `simultaneosly` | `simultaneously` |

---

## 🟢 Infra / Futuro

### 8. Health check endpoints

Adicionar `/health` em cada serviço + `healthcheck` no docker-compose.

### 9. README principal

README de 1 linha. Reescrever com arquitetura, tech stack, como rodar, screenshots, limitações.

### 10. Testes

Zero cobertura. MVP é aceitável sem, mas liste como limitação conhecida.

---

## ✅ Já corrigidos

| # | Descrição |
|---|-----------|
| 1 | Caminho `_model.pkl` → `_if_model.pkl` |
| 2 | Switch produção/teste falso |
| 3 | `dockerfile` lowercase → `Dockerfile` |
| 4 | `import sys` no `db_source.py` |
| 5 | `json.dumps()` no `raw_event` → dict direto |
| 6 | `CONTAMINATION` com fallback `0.01` |
| 7 | Split treino/teste + classification_report |
| 8 | Feature scaling com StandardScaler |
| 9 | print() → logging no consumer do detector |
| 10 | pending_count no backend |
| 11 | Página 404 com EmptyState |
| 12 | Link email placeholder |
| 13 | Dashboard.tsx → WorkersPage.tsx |

---

## 🎯 ROADMAP PARA 10/10 (LinkedIn Ready)

### Prioridade 1 — Quick Win (2-4 horas)

#### ✅ 11. Adicionar Testes Unitários
- [ ] Criar `tests/test_api_anomalies.py`
  - Testes dos endpoints GET/PUT `/api/anomalies`
  - Testes de status validation
  - Coverage mínimo: 70%
- [ ] Criar `tests/test_ml_worker.py`
  - Testar lógica de classificação (IF + RF)
  - Testar preprocessador
  - Testar judge_prediction com diferentes thresholds
- [ ] Adicionar `pytest.ini` com configuração
- [ ] Comando: `pytest --cov=. --cov-report=html`
- [ ] GitHub: reportar coverage nos PRs

#### ✅ 12. Completar README — Seções Vazias
- [ ] Expandir "## Comandos úteis"
  ```
  ### Docker
  docker-compose logs -f [service]
  docker-compose ps
  docker-compose restart [service]
  docker-compose down -v  # Remove volumes também
  
  ### Desenvolvimento
  docker-compose up --build
  docker-compose up -d     # Background mode
  ```
- [ ] Adicionar "## Troubleshooting"
  ```
  ### Port 3000 já está em uso
  lsof -i :3000 / netstat -ano | findstr :3000
  
  ### Modelo não treina
  - Verificar permissões em anomaly_detector/src/models
  - Verificar dados de seed em postgres-source
  
  ### Kafka não conecta
  - docker-compose logs kafka
  - Verificar se zookeeper está saudável
  ```

#### ✅ 13. Swagger Documentation
- [ ] Confirmar no README: "API Docs em http://localhost:8000/docs"
- [ ] Documentar tipos de response
- [ ] Adicionar exemplos nos schemas

#### ✅ 14. Criar LICENSE
- [ ] Escolher MIT (recomendado para portfólio)
- [ ] Criar arquivo `LICENSE` na raiz
- [ ] Adicionar SPDX header nos arquivos principais

---

### Prioridade 2 — Consolidação (4-6 horas)

#### ✅ 15. Documentação de ML
- [ ] Criar `docs/MODEL_DOCUMENTATION.md`
  ```
  ## Arquitetura do Modelo
  - Isolation Forest (detecção de anomalias)
  - Random Forest (classificação binária)
  - Por que híbrido? Combina diferentes perspectivas
  
  ## Thresholds
  - RF_HIGH_CONFIDENCE_THRESHOLD = 0.85
  - RF_MODERATE_THRESHOLD = 0.4
  - Explicar cada um
  
  ## Métricas
  - Precision, Recall, F1 em ambos datasets
  
  ## Retraining
  - Como e quando acontece
  - Frequência recomendada
  - Como validar novo modelo
  ```

#### ✅ 16. Health Checks nos Containers
- [ ] Adicionar em `docker-compose.yml`:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  ```
- [ ] Implementar `/health` endpoint em cada serviço
- [ ] Testar: `docker-compose ps` mostrará estado

#### ✅ 17. Environment Variables com Validação
- [ ] Criar `anomalies_hub_backend/config.py`
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      POSTGRES_USER: str
      POSTGRES_PASSWORD: str
      POSTGRES_DB: str
      POSTGRES_SERVER: str
      # Validação automática + .env loading
  ```
- [ ] Aplicar em todos serviços
- [ ] Gera erro claro se variável falta

#### ✅ 18. Logs Estruturados (JSON)
- [ ] Implementar em `anomalies_hub_backend/logging_config.py`
- [ ] Logs em JSON para melhor parsing
- [ ] Stack traces com contexto
- [ ] Aplicar em todos serviços

---

### Prioridade 3 — Profissionalismo (3-5 horas)

#### ✅ 19. CI/CD com GitHub Actions
- [ ] Criar `.github/workflows/tests.yml`
  ```yaml
  - name: Run tests
    run: pytest --cov
  
  - name: Lint backend
    run: black --check . && isort --check .
  
  - name: Lint frontend
    run: npm run lint
  
  - name: Build Docker images
    run: docker-compose build
  ```
- [ ] Badge no README com status

#### ✅ 20. Makefile para Comandos Comuns
- [ ] Criar `Makefile` na raiz
  ```makefile
  up:
  	docker-compose up
  
  logs:
  	docker-compose logs -f
  
  test:
  	pytest --cov
  
  lint:
  	black . && isort . && npm run lint
  
  build:
  	docker-compose build
  ```

#### ✅ 21. API Documentation Expandida
- [ ] Seção no README: "## API Reference"
  ```
  ### GET /api/anomalies
  Query: status, limit, offset, origin_table
  Response: { anomalies: [...], total: 123 }
  
  ### PUT /api/anomalies/{alert_id}/status
  Body: { status: "confirmed_fraud|false_positive|pending_revision" }
  
  ### GET /api/anomalies/stats
  Response: { total_anomalies, confirmed, false_positives, ... }
  ```

#### ✅ 22. Security Review
- [ ] Revisar credenciais em `docker-compose.yml`
- [ ] Mover para `.env.example` + `.env` (ignore no git)
- [ ] Usar `docker-compose.override.yml` para local
- [ ] Validar `.gitignore` está completo

---

### Prioridade 4 — Diferencial (2-3 horas)

#### ✅ 23. Demo Rápido com Dataset
- [ ] Criar `scripts/quickstart_demo.sh`
  ```bash
  #!/bin/bash
  docker-compose up -d
  sleep 30
  python scripts/seed_anomalies.py
  echo "✅ Sistema pronto! Acesse http://localhost:3000"
  docker-compose logs -f worker-insurance
  ```
- [ ] Documentar no README

#### ✅ 24. Dockerfile Otimizado (Multi-stage)
- [ ] Reduzir tamanho de imagens
- [ ] Cache de `requirements.txt` separado
- [ ] Exemplo:
  ```dockerfile
  FROM python:3.12-slim as builder
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  
  FROM python:3.12-slim
  COPY --from=builder /usr/local /usr/local
  COPY . /app
  ```

#### ✅ 25. Documentação de Arquitetura Expandida
- [ ] Expandir `docs/ARCHITECTURE.md`
  ```
  ## Decisões de Design
  - Por que Kafka e não RabbitMQ?
  - Por que Debezium e não Logstash?
  - Trade-offs: latência vs acurácia
  
  ## Scaling Considerations
  - Múltiplos workers por tabela
  - Horizontal scaling do Kafka
  - Limites de throughput
  ```

#### ✅ 26. Badges e Shields no README
- [ ] Adicionar no topo:
  ```
  [![Tests](https://github.com/user/repo/workflows/tests/badge.svg)](#)
  [![Coverage](https://codecov.io/gh/user/repo/branch/main/graph/badge.svg)](#)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#)
  [![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](#)
  ```

---

## 📊 Cronograma Recomendado

```
SEMANA 1:
  Seg-Ter: Prioridade 1 (#11-14)
  Qua-Qui: Prioridade 2 (#15-18)
  Sex:     Buffer + review

SEMANA 2:
  Seg-Ter: Prioridade 3 (#19-22)
  Qua-Qui: Prioridade 4 (#23-26)
  Sex:     Testes finais + publicar
```

---

## 🚀 QUICK WIN — Se Tiver 1 Hora

1. Completar README (Comandos + Troubleshooting) — 20min
2. Criar LICENSE (copiar template MIT) — 5min
3. Adicionar 3 testes simples (`tests/test_api.py`) — 30min
4. Fazer commit — 5min

**Resultado: 8.5 → 9.0 ⭐**

---

## Ordem de Ataque Anterior

```
Agora (10 min):       #1 (print handler), #2 (CORS)
Essa semana:           #3 (link email), #7 (typos)
Antes de postar:       #9 (README)
Depois:                #4 (Python 3.12), #5 (senhas scripts), #6 (.dockerignore), #8 (health checks)
Futuro:                #10 (testes)
```
