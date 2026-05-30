# TODO — Correções e Melhorias para o FraudOps

Lista completa do que precisa ser ajustado para o projeto ficar 100% profissional para publicação no LinkedIn.

---

## Bugs (Precisam ser corrigidos — o projeto não funciona 100% sem isso)

### 1. Caminho incorreto do modelo — treinamento roda sempre

**Arquivo:** `anomaly_detector/main.py` — linha 26

**Problema:** O código verifica se `_model.pkl` existe, mas o arquivo real é salvo como `_if_model.pkl`. Resultado: mesmo com modelos já treinados, o treinamento inicial é executado toda vez que o container sobe.

```python
# ERRADO (linha 26):
MODEL_PATH = f'models/{TARGET_TABLE}_model.pkl'

# CERTO:
MODEL_PATH = f'models/{TARGET_TABLE}_if_model.pkl'
```

Além disso, a variável `TRANSLATOR_PATH` (linha 25) nunca é usada. Pode remover ou usar na verificação também.

---

### 2. Switch de produção/teste falso

**Arquivo:** `anomaly_handler/main.py` — linhas 5-6

**Problema:** Importa a mesma classe duas vezes com nomes diferentes, achando que são diferentes. O `if is_production` nunca muda nada, porque as duas branches executam exatamente o mesmo código.

```python
# ERRADO:
from src.handler.handler import AnomalyHandler as AnomalyHandlerTest
from src.handler.handler import AnomalyHandler

# ... if is_production: AnomalyHandlerClass = AnomalyHandler
#     else: AnomalyHandlerClass = AnomalyHandlerTest  # mesma classe!

# CERTO — se quiser switch real, crie uma classe de teste separada.
# Ou simplesmente remova o switch e use direto:
from src.handler.handler import AnomalyHandler
handler = AnomalyHandler(group_id=GROUP_ID)
handler.handle_anomalies()
```

---

### 3. Dockerfile duplicado no anomaly_handler

**Arquivos:**
- `anomaly_handler/Dockerfile` (raiz do handler)
- `anomaly_handler/src/Dockerfile` (dentro de src)

**Problema:** O docker-compose usa `context: ./anomaly_handler`, então o Docker vai procurar `Dockerfile` na raiz do handler. Se ele estiver vazio ou for o errado, o build quebra. Verifique qual dos dois Dockerfiles está correto e:
- Delete o errado, OU
- Altere o docker-compose para apontar pro certo: `dockerfile: src/Dockerfile`

---

## Melhorias do Modelo ML (Credibilidade técnica)

### 4. Documentar os thresholds do modelo híbrido

**Arquivo:** `anomaly_detector/src/interference_pipeline/worker.py` — `_judge_prediction()` (linhas 101-124)

**Problema:** Os thresholds 0.85, 0.4, -0.15, -0.1 são números mágicos sem explicação. Para o LinkedIn, você precisa conseguir explicar como chegou nesses valores.

**Sugestão:** Adicione um comentário explicando a lógica ou mova os thresholds para constantes nomeadas no topo do arquivo:

```python
# No topo do worker.py ou como variáveis de ambiente:
RF_HIGH_CONFIDENCE_THRESHOLD = 0.85   # RF sozinho dispara anomalia
RF_MODERATE_THRESHOLD = 0.4           # RF + IF combinados
IF_COMBINED_THRESHOLD = -0.15         # IF para voto combinado
IF_STANDALONE_THRESHOLD = -0.1        # IF sozinho dispara anomalia
```

---

### 5. contamination=0.1 muito alto

**Arquivos:**
- `anomaly_detector/src/training_pipeline/workers/worker_models_initial.py` — linha 41
- `anomaly_detector/src/training_pipeline/workers/worker_models_retraining.py` — linha 66

**Problema:** `contamination=0.1` assume que 10% dos dados são fraude. Em cenário real, fraude costuma ser <1%. Isso gera muitos falsos positivos.

**Sugestão:** Tornar configurável por variável de ambiente:

```python
contamination = float(os.getenv("CONTAMINATION", "0.01"))
i_forest = IsolationForest(contamination=contamination, random_state=42)
```

---

### 6. Dados não-rotulados viram negativos no Random Forest

**Arquivo:** `anomaly_detector/src/training_pipeline/workers/worker_models_retraining.py` — linha 22

**Problema:** `df_source['is_fraud'] = 0` define TODOS os dados como "não-fraude", e depois só atualiza os que têm label. Isso faz o RF aprender que dados não revisados são normais — o que introduz viés, porque dados não revisados podem sim ser fraude.

**Sugestão:** Treinar o Random Forest **apenas** com dados que têm label (confirmed_fraud + false_positive), em vez de usar a tabela inteira:

```python
# Em vez de df_source inteiro, filtrar só os que têm label:
labeled_ids = df_history['original_id'].unique()
df_labeled = df_source[df_source['id'].isin(labeled_ids)].copy()
```

---

### 7. Sem split treino/teste — sem métricas de validação

**Arquivo:** `anomaly_detector/src/training_pipeline/workers/worker_models_retraining.py`

**Problema:** Após o retreino, não há como saber se o modelo melhorou ou piorou. Nenhuma métrica é calculada além da precision no dashboard.

**Sugestão:** Adicionar `train_test_split` e calcular métricas básicas:

```python
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
r_forest.fit(X_train, y_train)
y_pred = r_forest.predict(X_test)
logging.info(f"Random Forest performance:\n{classification_report(y_test, y_pred)}")
```

---

### 8. Sem feature scaling

**Arquivos:** `anomaly_detector/src/training_pipeline/workers/worker_models_initial.py` e `worker_models_retraining.py`

**Problema:** DictVectorizer só transforma categóricas em one-hot, mas não escala features numéricas (V1, V2, V3... Amount). O Isolation Forest é sensível a escala — features com range maior dominam o cálculo de anomalia.

**Sugestão:** Adicionar `StandardScaler` no pipeline:

```python
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('vectorizer', DictVectorizer(sparse=False)),
    ('scaler', StandardScaler()),
    ('model', IsolationForest(contamination=contamination, random_state=42))
])
pipeline.fit(data_dict)
```

Se adicionar o scaler, precisa salvar o pipeline inteiro (não só o translator) e atualizar o `DynamicPreprocessor` para aplicar o scaler também.

---

## Melhorias de Código (Profissionalismo)

### 9. Substituir print() por logging

**Arquivo:** `anomaly_detector/src/interference_pipeline/consumer/consumer.py` — linhas 22 e 35

```python
# ERRADO:
print(f"Conected to kafka, listenin on topic: {topic}...")
print(f"Error: {msg.error()}")

# CERTO:
logging.info(f"Connected to Kafka, listening on topic: {topic}...")
logging.error(f"Kafka error: {msg.error()}")
```

---

### 10. pending_count nunca é populado

**Arquivos:**
- `anomalies_hub_backend/crud/pipeline.py` — `get_all_pipelines()`
- `anomalies_hub_frontend/anomalies_hub_frontend/src/types/types.ts` — interface `Pipeline`

**Problema:** O frontend espera um campo `pending_count?`, mas o backend nunca calcula esse valor. Ou implemente no backend, ou remova do tipo do frontend.

**Sugestão para implementar no backend:** Adicionar uma subquery ou JOIN na query de pipelines:

```python
def get_all_pipelines(engine: Engine):
    query = text("""
        SELECT p.*,
            COALESCE(a.pending, 0) as pending_count
        FROM pipelines_config p
        LEFT JOIN (
            SELECT origin_table, COUNT(*) as pending
            FROM anomalies_history
            WHERE status = 'pending_revision'
            GROUP BY origin_table
        ) a ON a.origin_table = p.target_table
        ORDER BY p.last_startup DESC
    """)
```

---

### 11. Página 404 sem estilo

**Arquivo:** `anomalies_hub_frontend/anomalies_hub_frontend/src/routes/routes.tsx` — linha 21

**Problema:** A rota 404 é um `<h2>` solto com emoji, fora do padrão visual do projeto.

**Sugestão:** Usar o componente `EmptyState` que você já tem:

```tsx
import { EmptyState } from '../components/ui';
import { FileQuestion } from 'lucide-react';

// Na rota:
<Route path="*" element={
  <EmptyState
    icon={FileQuestion}
    title="Page not found"
    description="The page you are looking for doesn't exist."
  />
} />
```

---

### 12. Link do dashboard no email é placeholder

**Arquivo:** `anomaly_handler/src/handler/handler.py` — linha 116

**Problema:** O botão "Review in Dashboard" no email tem `href="#"`.

**Sugestão:** Adicionar a URL do frontend como variável de ambiente:

```python
dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
# No HTML: href="{dashboard_url}/revisions/{table_name}"
```

---

### 13. Nome do arquivo não bate com o componente

**Arquivo:** `anomalies_hub_frontend/anomalies_hub_frontend/src/pages/Dashboard.tsx`

**Problema:** O arquivo se chama `Dashboard.tsx` mas exporta `WorkersPage`. Renomeie o componente para `DashboardPage` ou renomeie o arquivo para `WorkersPage.tsx`.

---

## Melhorias de Infraestrutura

### 14. Health check endpoints

Adicionar um endpoint simples em cada serviço para o Docker verificar se está vivo:

```python
# No hub-backend (main.py):
@app.get("/health")
def health():
    return {"status": "ok"}
```

No docker-compose:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

### 15. README principal

**Arquivo:** `README.md` na raiz do projeto

Atualmente tem 1 linha. Precisa de um README completo para o LinkedIn. Estrutura sugerida:

```markdown
# FraudOps — Real-Time Anomaly Detection Platform

Sistema de detecção de anomalias em tempo real usando um modelo híbrido de
Machine Learning (Isolation Forest + Random Forest) com pipeline de streaming
Kafka e dashboard React para revisão humana.

## Arquitetura
[diagrama ou descrição da pipeline]

## Tecnologias
- **Streaming**: Apache Kafka + Debezium CDC
- **ML**: scikit-learn (Isolation Forest, Random Forest, DictVectorizer)
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React 19 + TypeScript + TailwindCSS 4
- **Infra**: Docker Compose (9 serviços)

## O Modelo Híbrido
[explicação do Isolation Forest + Random Forest e a lógica de votação]

## Como Rodar
1. Clone o repositório
2. Configure o .env
3. `docker-compose up`
4. Acesse http://localhost:3000

## Screenshots
[prints das 3 telas]

## Limitações Conhecidas
- Sem autenticação na API
- Thresholds do modelo são fixos
- Sem validação cruzada no retreino
```

---

## Ordem Sugerida de Implementação

1. **Bugs:** #1 (caminho modelo), #2 (switch falso), #3 (Dockerfile duplicado)
2. **README:** #15 (essencial para LinkedIn)
3. **ML:** #5 (contamination configurável), #4 (documentar thresholds)
4. **Código:** #9 (print→logging), #10 (pending_count), #11 (404), #13 (rename)
5. **ML Avançado:** #6 (dados rotulados), #7 (métricas), #8 (feature scaling)
6. **Infra:** #12 (link email), #14 (health checks)
