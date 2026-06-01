# TODO — Correções e Melhorias para o FraudOps

Lista completa do que precisa ser ajustado para o projeto ficar 100% profissional para publicação no LinkedIn.

---

## Bugs (Precisam ser corrigidos — o projeto não funciona 100% sem isso)

### 1. ✅ Caminho incorreto do modelo — ~~treinamento roda sempre~~ CORRIGIDO

**Arquivo:** `anomaly_detector/main.py` — linha 26

**Problema:** O código verificava se `_model.pkl` existe, mas o arquivo real é salvo como `_if_model.pkl`.

**Status:** Já corrigido — usa `_if_model.pkl`.

---

### 2. ✅ Switch de produção/teste falso — CORRIGIDO

**Arquivo:** `anomaly_handler/main.py`

**Problema:** Importava a mesma classe duas vezes com nomes diferentes.

**Status:** Já corrigido — import direto sem switch falso.

---

### 3. Dockerfile duplicado no anomaly_handler

**Arquivos:**
- `anomaly_handler/dockerfile` (raiz do handler — lowercase!)
- `anomaly_handler/src/main.py` (duplicado do `main.py` raiz)

**Problema:** O arquivo se chama `dockerfile` (minúsculo). Em Linux (produção), Docker espera `Dockerfile` com D maiúsculo — o build quebra. Além disso, `src/main.py` é uma cópia idêntica do `main.py` raiz.

**Correção:**
1. Renomear `dockerfile` → `Dockerfile`
2. Deletar `anomaly_handler/src/main.py` (duplicado do raiz)

---

### 4. `sys.exit(1)` sem `import sys` — crash em produção

**Arquivo:** `anomaly_detector/src/training_pipeline/db/db_source.py` — linha 32

**Problema:** Chama `sys.exit(1)` mas nunca fez `import sys`. Se uma variável de ambiente obrigatória estiver faltando, o container vai crashar com `NameError: name 'sys' is not defined` em vez de dar um erro claro. O `db_internal.py` importa corretamente — foi esquecido só nesse arquivo.

```python
# ERRADO (linha 32):
sys.exit(1)  # sys nunca foi importado

# CERTO — adicionar no topo:
import sys
```

---

### 5. `json.dumps()` quebra consulta JSONB no retreino

**Arquivo:** `anomaly_handler/src/handler/handler.py` — linha 170

**Problema:** A coluna `raw_event` é `JSONB`, mas o insert usa `json.dumps(event_json...)`, que converte o dict em **string**. O PostgreSQL armazena como string-encoded em vez de objeto JSONB nativo. Resultado: a query de retreino em `worker_models_retraining.py` (linha 32) que faz `raw_event->>'id'` **não funciona** — o operador `->>` em uma string retorna null.

```python
# ERRADO:
"raw_event": json.dumps(event_json.get('raw_event', {}))

# CERTO — passar o dict direto, o driver psycopg2 sabe serializar:
"raw_event": event_json.get('raw_event', {})
```

---

### 6. `CONTAMINATION` sem fallback — TypeError se env var faltar

**Arquivos:**
- `anomaly_detector/src/training_pipeline/workers/worker_models_initial.py` — linha 13
- `anomaly_detector/src/training_pipeline/workers/worker_models_retraining.py` — linha 20

**Problema:** `float(os.getenv("CONTAMINATION"))` — se a variável não estiver definida, `float(None)` lança `TypeError`.

```python
# CERTO:
contamination = float(os.getenv("CONTAMINATION", "0.01"))
```

---

## Melhorias do Modelo ML (Credibilidade técnica)

### 7. ✅ Split treino/teste com métricas — CORRIGIDO

**Status:** Já implementado no retreino com `train_test_split` + `classification_report`.

---

### 8. ✅ Feature scaling com StandardScaler — CORRIGIDO

**Status:** Implementado. Ambos os workers de treino salvam `_scaler.pkl`, e o `DynamicPreprocessor` carrega e aplica na inferência, com fallback para modelos antigos.

---

### 9. ✅ Substituir print() por logging — CORRIGIDO

---

### 10. ✅ pending_count populado no backend — CORRIGIDO

---

## Melhorias de Código (Profissionalismo)

### 11. ✅ Página 404 com EmptyState — CORRIGIDO

---

### 12. Link do dashboard no email é placeholder

**Arquivo:** `anomaly_handler/src/handler/handler.py` — linha 116

**Problema:** O botão "Review in Dashboard" no email tem `href="#"`.

**Sugestão:** Adicionar a URL do frontend como variável de ambiente:
```python
dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
```

---

### 13. ✅ Nome do arquivo bate com componente — CORRIGIDO

`Dashboard.tsx` → `WorkersPage.tsx`

---

### 14. Versões de Python inconsistentes nos Dockerfiles

**Arquivos:**
- `anomaly_detector/Dockerfile` — `python:3.10-slim`
- `anomaly_handler/dockerfile` — `python:3.10-slim`
- `anomalies_hub_backend/Dockerfile` — `python:3.12-slim`

**Problema:** Versões diferentes entre serviços podem causar bugs sutis com bibliotecas compartilhadas. Padronizar para `python:3.12-slim` em todos.

---

### 15. Senhas hardcoded nos scripts de seed

**Arquivos:**
- `scripts/seed_anomalies.py` — linhas 23-24
- `fake_datasets_seed/dataset_seed.py` — linha 7

**Problema:** Credenciais de banco fixas no código. Deveriam ler de `.env`.

---

### 16. Sem `.dockerignore` em nenhum serviço

**Problema:** `.venv`, `__pycache__`, `.csv`, e `.pkl` podem ser copiados para dentro das imagens Docker, inchando o build.

**Sugestão:** Criar `.dockerignore` em cada serviço:
```
__pycache__
.venv
*.pyc
*.csv
*.pkl
models/
```

---

### 17. Typos espalhados pelo código

| Arquivo | Linha | Erro | Correção |
|---------|-------|------|----------|
| `anomaly_detector/main.py` | 34 | `occured` | `occurred` |
| `anomaly_handler/main.py` | 16 | `occured` | `occurred` |
| `anomaly_detector/.../consumer.py` | 50 | `occured` | `occurred` |
| `anomaly_handler/.../consumer.py` | 46 | `occured` | `occurred` |
| `anomaly_detector/.../producer.py` | 34 | `Faild` | `Failed` |
| `anomaly_handler/.../db.py` | 32 | `databese` | `database` |
| `anomaly_detector/.../worker_models_retraining.py` | 7,23 | `iternal` | `internal` |
| `anomaly_handler/.../handler.py` | 16,61 | `reciever` | `receiver` |
| `anomaly_detector/.../worker.py` | 108 | `simultaneosly` | `simultaneously` |

---

## Melhorias de Infraestrutura

### 18. Health check endpoints

Adicionar endpoint `/health` em cada serviço + `healthcheck` no docker-compose.

---

### 19. README principal

README de 1 linha. Precisa de README completo — arquitetura, tech stack, como rodar, screenshots, limitações.

---

### 20. Sem testes

Projeto tem zero cobertura de testes. Para MVP é aceitável, mas deve ser listado como limitação conhecida. Adicionar pelo menos testes de integração para o pipeline de inferência.

---

## Ordem Sugerida de Implementação

1. **Críticos:** #4 (`import sys`), #5 (JSONB quebrado), #3 (dockerfile lowercase + main.py duplicado)
2. **Setup:** #19 (README), #18 (health checks)
3. **Bugs menores:** #6 (CONTAMINATION fallback), #15 (senhas hardcoded)
4. **Polimento:** #17 (typos), #14 (versões Python), #16 (.dockerignore), #12 (link email)
5. **Futuro:** #20 (testes)
