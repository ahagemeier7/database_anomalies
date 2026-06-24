
# Plan: Model Version Selection (frontend + backend)

## TL;DR
Permitir que o frontend liste e ative versões de modelo; o backend deve armazenar metadados em `model_versions`; o inference worker deve carregar a versão ativa (ou a versão explicitamente selecionada). Manteremos arquivos `latest` como alias para compatibilidade.

## Priority
- **Alta:** Fazer com que o `anomaly_detector` consiga usar modelos versionados explicitamente (consultando a versão ativa via DB/API ou carregando por `version`), com fallback para os aliases `latest`. Este item é crítico para colocar versões em produção com segurança.

## Steps

1. Criar a tabela `model_versions` no banco interno e adicionar a coluna `active_model_version` em `pipelines_config` (depende do passo 2).
2. Implementar CRUD para `model_versions` em `anomalies_hub_backend/crud/pipeline.py` (list / get / activate).
3. Expor endpoints REST no backend:

```http
GET  /api/pipelines/{target_table}/versions        # lista versões
GET  /api/pipelines/{target_table}/versions/active # versão ativa
POST /api/pipelines/{target_table}/versions/{version}/activate # ativa versão
```

4. Adicionar Pydantic schemas em `anomalies_hub_backend/schemas/schemas.py` para `ModelVersion` e respostas.
5. Estender `anomaly_detector/src/training_pipeline/workers/model_versioning.py` para retornar metadados e inserir um registro em `model_versions` (paths, métricas, created_at) após salvar os artefatos.
--Feito--

6. Atualizar `retrain_hybrid_models` e `train_models` para coletar métricas básicas (ex.: número de amostras, precision/recall quando disponível) e passá-las para a rotina de persistência de versão.
7. Atualizar `anomaly_detector/src/interference_pipeline/worker.py` e `anomaly_detector/src/interference_pipeline/preprocessing_data/preprocess_data.py` para suportar carregar modelos por `version` e/ou consultar a versão ativa via DB/API.
8. Frontend (`anomalies_hub_frontend`):
	- Adicionar o type `ModelVersion` em `anomalies_hub_frontend/anomalies_hub_frontend/src/types/types.ts`.
	- Implementar `listModelVersions()` e `activateModelVersion()` em `anomalies_hub_frontend/anomalies_hub_frontend/src/services/services.ts`.
	- Adicionar UI (dropdown ou modal) em `anomalies_hub_frontend/anomalies_hub_frontend/src/pages/WorkersPage.tsx` para seleção de versão; opcionalmente criar `ModelVersionsPage.tsx` para histórico detalhado.
9. Mecanismo de ativação: ao ativar, o backend deve marcar `is_active = true` para a versão escolhida e `is_active = false` para as demais (transação única). Atualizar `pipelines_config.active_model_version` ou manter o join nas consultas.
10. Verificação e testes: garantir que os endpoints retornam a lista correta, que a ativação altera `model_versions` e `pipelines_config`, que o worker carrega a versão ativa e que o frontend reflete o estado.

## Relevant files

- `anomalies_hub_backend/crud/pipeline.py`
- `anomalies_hub_backend/api/pipeline.py`
- `anomalies_hub_backend/schemas/schemas.py`
- `anomaly_detector/src/training_pipeline/workers/model_versioning.py`
- `anomaly_detector/src/training_pipeline/workers/worker_models_retraining.py`
- `anomaly_detector/src/training_pipeline/workers/worker_models_initial.py`
- `anomaly_detector/src/interference_pipeline/worker.py`
- `anomaly_detector/src/interference_pipeline/preprocessing_data/preprocess_data.py`
- `anomalies_hub_frontend/anomalies_hub_frontend/src/services/services.ts`
- `anomalies_hub_frontend/anomalies_hub_frontend/src/pages/WorkersPage.tsx`
- `anomalies_hub_frontend/anomalies_hub_frontend/src/types/types.ts`

## Verification

1. DB: `SELECT * FROM model_versions WHERE target_table = 'your_table' ORDER BY created_at DESC;` — confirmar registros e campo `is_active`.
2. API: `GET /api/pipelines/{table}/versions` retorna a lista de versões.
3. Activation: `POST /api/pipelines/{table}/versions/{version}/activate` marca a versão ativa e atualiza `pipelines_config.active_model_version` (se utilizado).
4. Worker: reiniciar ou validar hot-reload; confirmar que o worker carrega os artefatos apontados pelo registro ativo.
5. Frontend: UI mostra versões, flag `active` e permite ativação via chamada à API.

## Decisions

- Formato de versão: `v{sequence:03d}` (ex.: `v001`) — já implementado e fácil de ordenar lexicograficamente.
- Ativação: apenas uma versão ativa por `target_table`, aplicada em transação.
- Compatibilidade: manter gravação de aliases `latest` em disco para compatibilidade com código atual; a inferência deve preferir paths versionados quando especificados.

## Further Considerations

- Worker reload strategy: consultar versão ativa em intervalos/batches e aplicar swap gradual para evitar inconsistência durante a predição.
- Métricas: armazenar precision/recall e tamanho do conjunto de treino em `model_versions` para exibição no frontend.
- Rollback: permitir ativação de versões anteriores via endpoint para rollback rápido.

---