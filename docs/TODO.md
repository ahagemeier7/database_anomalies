
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
