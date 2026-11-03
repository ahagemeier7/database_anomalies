# Documentação dos modelos de detecção

## Objetivo

O projeto demonstra uma pipeline de detecção de anomalias para a tabela `creditcard_transactions`. O fluxo consome alterações capturadas por CDC, classifica eventos potencialmente anômalos e permite que uma pessoa marque cada alerta como fraude confirmada ou falso positivo no Hub.

O dataset ativo de demonstração é `creditcard_small.csv`, uma amostra do [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud). A coluna `Class` é usada pelo seed e pelo benchmark offline. No retreinamento supervisionado, os rótulos vêm das decisões humanas. Ela é removida das features de inferência.

## Pré-processamento

- As colunas configuradas em `COLUMNS_TO_IGNORE` são removidas antes da inferência. No cenário padrão: `id`, `Class`, `PolicyNumber` e `RepNumber`.
- Os registros são convertidos em vetores numéricos com `DictVectorizer`.
- `StandardScaler` é ajustado no treinamento e reaplicado na inferência para manter uma transformação consistente entre treinamento e inferência. Os modelos baseados em árvores não exigem padronização por escala.
- O vetor e o scaler são versionados junto dos modelos para que treinamento e inferência usem a mesma transformação.

## Modelos e ciclo de vida

### Treinamento inicial

Na primeira execução, o worker espera a tabela de origem receber dados e treina um `IsolationForest`. Esse modelo não supervisionado é apropriado quando ainda não existem decisões humanas registradas. A contaminação padrão é `0.01` e o `random_state` é `42` para tornar o experimento reproduzível.

### Retreinamento supervisionado

O endpoint de retreinamento consulta as decisões do Hub. Alertas `confirmed_fraud` recebem rótulo 1 e `false_positive` recebem rótulo 0. Quando existem exemplos confirmados de ambas as classes, o projeto treina um `RandomForestClassifier` com 100 árvores. A divisão estratificada 80/20 só publica precisão, recall e F1 quando treino e teste comportam ambas as classes. O vetor e o scaler dessa avaliação são ajustados exclusivamente no treino. Com poucos exemplos de ambas as classes, o Random Forest é treinado sem métricas de validação. O modelo final usa todos os registros revisados de ambas as classes.

Se não houver revisões de ambas as classes, apenas o `IsolationForest` permanece disponível. Se a pipeline estiver em `rf`, o retreinamento muda seu modo para `if` ao ativar uma versão sem Random Forest. O worker também faz fallback para Isolation Forest no modo híbrido quando o Random Forest não está disponível.

### Inferência

O modo `hybrid` combina os dois modelos:

- Random Forest com probabilidade acima de `0.85`: gera alerta.
- Random Forest acima de `0.40` e Isolation Forest abaixo de `-0.15`: gera alerta combinado.
- Isolation Forest abaixo de `-0.10`: gera alerta mesmo sem confirmação do Random Forest.

Os limites são configuráveis pelas variáveis `RF_HIGH_CONFIDENCE_THRESHOLD`, `RF_MODERATE_THRESHOLD`, `IF_COMBINED_THRESHOLD` e `IF_STANDALONE_THRESHOLD`. Eles são parâmetros de demonstração, não limites validados para produção.

O treinamento inicial registra a pipeline no modo `if`. Após haver pelo menos uma fraude confirmada e um falso positivo, execute o retreinamento e selecione `hybrid` no Hub para usar os dois modelos. O modo `rf` fica desabilitado no Hub e é rejeitado pela API quando não há artefato de Random Forest na versão ativa. Uma falha ao carregar um novo conjunto preserva o conjunto anterior. A seleção manual de uma versão sem Random Forest é rejeitada enquanto a pipeline estiver em `rf`; selecione `if` ou `hybrid` antes.

## Versionamento e métricas

Cada treinamento salva vetor, scaler, Isolation Forest e, quando aplicável, Random Forest em uma versão registrada no banco interno. A versão ativa é consultada pelo worker e pode ser trocada pelo Hub.

O registro da versão armazena número de amostras, quantidade de features, existência do modelo supervisionado, dados rotulados, fraudes confirmadas e, quando a validação é possível, precisão, recall e F1. Essas métricas devem ser interpretadas com cautela quando há poucas revisões humanas.

## Limitações

- O dataset é uma amostra de demonstração e não representa um ambiente de produção.
- A qualidade do Random Forest depende diretamente da quantidade e da qualidade das decisões humanas.
- O Isolation Forest detecta desvio estatístico, não fraude comprovada; todo alerta requer revisão.
- O projeto não inclui monitoramento de drift, calibração automática de thresholds ou avaliação externa contínua.

## Avaliação offline

O benchmark usa a amostra rotulada, com conjuntos separados por grupos de features idênticas e semente 42. As proporções são aproximadamente 60% treino, 20% validação e 20% teste; os thresholds são escolhidos somente na validação. A configuração, a impressão digital dos dados e as métricas ficam em `model_testing/`, com gráficos reproduzidos em `docs/model_testing/`.

O benchmark usa hiperparâmetros e thresholds próprios e não mede o fluxo Kafka ou o modelo inicial da demonstração. Na execução publicada, Random Forest e híbrido tiveram as mesmas previsões no teste. As métricas de retreinamento refletem apenas os alertas revisados, uma amostra selecionada pelo detector, e não estimam o desempenho sobre todas as transações.
