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

## Ordem de Ataque

```
Agora (10 min):       #1 (print handler), #2 (CORS)
Essa semana:           #3 (link email), #7 (typos)
Antes de postar:       #9 (README)
Depois:                #4 (Python 3.12), #5 (senhas scripts), #6 (.dockerignore), #8 (health checks)
Futuro:                #10 (testes)
```
