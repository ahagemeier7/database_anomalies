# Documentação dos modelos de detecção

## Objetivo

O projeto demonstra uma pipeline de detecção de anomalias para a tabela `creditcard_transactions`. O fluxo consome alterações capturadas por CDC, classifica eventos potencialmente anômalos e permite que uma pessoa marque cada alerta como fraude confirmada ou falso positivo no Hub.

O dataset ativo de demonstração é `creditcard_small.csv`, uma amostra do [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud). A coluna `Class` é usada somente pelo seed e pelo retreinamento; ela não é usada como feature de inferência.

## Pré-processamento

- As colunas configuradas em `COLUMNS_TO_IGNORE` são removidas antes da inferência. No cenário padrão: `id`, `Class`, `PolicyNumber` e `RepNumber`.
- Os registros são convertidos em vetores numéricos com `DictVectorizer`.
- `StandardScaler` é ajustado no treinamento e reaplicado na inferência para evitar que atributos com escalas maiores dominem o resultado.
- O vetor e o scaler são versionados junto dos modelos para que treinamento e inferência usem a mesma transformação.

## Modelos e ciclo de vida

### Treinamento inicial

Na primeira execução, o worker espera a tabela de origem receber dados e treina um `IsolationForest`. Esse modelo não supervisionado é apropriado quando ainda não existem decisões humanas registradas. A contaminação padrão é `0.01` e o `random_state` é `42` para tornar o experimento reproduzível.

### Retreinamento supervisionado

O endpoint de retreinamento consulta as decisões do Hub. Alertas `confirmed_fraud` recebem rótulo 1 e `false_positive` recebem rótulo 0. Quando existem exemplos confirmados de ambas as classes, o projeto treina um `RandomForestClassifier` com 100 árvores. Se cada classe possuir ao menos duas amostras, é feita uma divisão estratificada 80/20 para calcular precisão, recall e F1; em seguida o modelo final é reajustado com todos os dados rotulados.

Se não houver dados rotulados suficientes, apenas o `IsolationForest` permanece disponível. O worker também faz fallback para esse modo quando o arquivo do Random Forest não está disponível.

### Inferência

O modo `hybrid` combina os dois modelos:

- Random Forest com probabilidade acima de `0.85`: gera alerta.
- Random Forest acima de `0.40` e Isolation Forest abaixo de `-0.15`: gera alerta combinado.
- Isolation Forest abaixo de `-0.10`: gera alerta mesmo sem confirmação do Random Forest.

Os limites são configuráveis pelas variáveis `RF_HIGH_CONFIDENCE_THRESHOLD`, `RF_MODERATE_THRESHOLD`, `IF_COMBINED_THRESHOLD` e `IF_STANDALONE_THRESHOLD`. Eles são parâmetros de demonstração, não limites validados para produção.

O treinamento inicial registra a pipeline no modo `if`. Após haver pelo menos uma fraude confirmada e um falso positivo, execute o retreinamento e selecione `hybrid` no Hub para usar os dois modelos. O modo `rf` só deve ser escolhido quando houver um Random Forest treinado.

## Versionamento e métricas

Cada treinamento salva vetor, scaler, Isolation Forest e, quando aplicável, Random Forest em uma versão registrada no banco interno. A versão ativa é consultada pelo worker e pode ser trocada pelo Hub.

O registro da versão armazena número de amostras, quantidade de features, existência do modelo supervisionado, dados rotulados, fraudes confirmadas e, quando a validação é possível, precisão, recall e F1. Essas métricas devem ser interpretadas com cautela quando há poucas revisões humanas.

## Limitações

- O dataset é uma amostra de demonstração e não representa um ambiente de produção.
- A qualidade do Random Forest depende diretamente da quantidade e da qualidade das decisões humanas.
- O Isolation Forest detecta desvio estatístico, não fraude comprovada; todo alerta requer revisão.
- O projeto não inclui monitoramento de drift, calibração automática de thresholds ou avaliação externa contínua.
