# Roteiro de publicação no LinkedIn

Este documento organiza o que precisa ser feito antes de publicar o projeto de detecção de anomalias no LinkedIn e no GitHub.

## Status da auditoria

Última verificação: 28/08/2026, após nova execução do ambiente.

- **Testes automatizados:** concluído, 19 testes aprovados com `pytest` usando `.venv`.
- **Configuração Docker Compose:** concluído, `docker compose config` passou.
- **Ambiente em execução:** concluído; todos os serviços principais subiram, com PostgreSQL e Kafka saudáveis.
- **Interfaces HTTP:** concluído; frontend, Swagger, Kafka UI e Kafka Connect responderam com HTTP 200.
- **Seed do dataset principal:** concluído; 15.000 registros normais e 492 fraudes foram inseridos com código 0.
- **Demonstração ponta a ponta:** concluída; 112 alertas foram persistidos em `anomalies_history`, revisados pela API e exibidos no dashboard. O screenshot foi fornecido para a publicação.
- **Validação dos alertas contra o CSV:** concluída offline; 104 dos 112 alertas eram fraudes reais e 8 eram falsos positivos.
- **Métricas do experimento:** concluídas; a tela mostra 104 fraudes confirmadas, 8 falsos positivos e precision 92,9%. A validação offline também calculou recall 21,14% e F1-score 34,44%.
- **Diagrama:** validado; o Detector acessa o banco interno para registrar a pipeline e as versões dos modelos, enquanto publica os alertas no tópico `detected_anomalies` para o Handler persistir em `anomalies_history`.
- **Documentação de modelos:** pendente; `docs/Model_Documentation.md` ainda contém apenas tópicos.
- **Materiais para LinkedIn:** parcialmente concluídos; o screenshot do dashboard foi obtido, mas ainda faltam gráfico dedicado, vídeo e imagem de capa.
- **Segundo dataset:** ainda não validado ponta a ponta e não deve ser priorizado antes da avaliação do fluxo principal.

### Próximo passo recomendado

Capturar o vídeo do fluxo e concluir a documentação dos modelos. A geração, classificação, persistência e exibição dos alertas já foram validadas.

## 1. Objetivo da publicação

Apresentar o projeto como um case de integração entre:

- engenharia de dados;
- processamento orientado a eventos;
- machine learning;
- APIs e interfaces web;
- execução de serviços distribuídos com Docker.

A mensagem principal deve ser:

> Construí uma plataforma de detecção de anomalias que captura alterações em um banco PostgreSQL, publica eventos no Kafka, aplica modelos de Machine Learning e disponibiliza os alertas em um dashboard para investigação.

O projeto deve ser apresentado como um projeto de estudo e portfólio. Não afirmar que é uma solução pronta para produção.

## 2. Critério de pronto para publicar

Só publicar quando todos os itens abaixo estiverem concluídos:

- [ ] Uma pessoa consegue clonar o repositório e entender o objetivo em menos de dois minutos.
- [x] O projeto sobe seguindo um fluxo documentado. `docker compose up --build -d` subiu os serviços principais.
- [x] Existe um caminho reproduzível para inserir dados e gerar uma anomalia. O seed inseriu os dados e gerou 112 alertas persistidos.
- [x] O dashboard mostra alertas reais do fluxo: screenshot com 104 fraudes confirmadas, 8 falsos positivos e precision de 92,9%.
- [x] Os testes automatizados passam: 19 testes aprovados.
- [x] Existem métricas calculadas para o experimento: precision 92,86%, recall 21,14% e F1-score 34,44%.
- [x] Existem métricas exibidas no dashboard: 104 fraudes confirmadas, 8 falsos positivos e precision de 92,9%.
- [ ] Não há senhas pessoais, tokens ou dados privados versionados. **Pendente:** há credenciais fictícias hardcoded no Compose; confirmar que nenhuma é real antes do push.
- [x] O diagrama da arquitetura está atualizado com o fluxo real. A seta Detector -> Internal DB representa `pipelines_config` e `model_versions`; o fluxo dos alertas é `Detector -> detected_anomalies -> Handler -> anomalies_history`.
- [x] O README não promete comportamento que ainda não foi medido. A contagem de serviços e o tamanho real do seed foram corrigidos; as métricas estão identificadas como experimentais.
- [ ] O link do GitHub, imagens e vídeo estão revisados.

## 3. Fase 1: organizar o repositório

### 3.1 Revisar a documentação

Atualizar o README para conter, nesta ordem:

1. nome do projeto e uma frase de posicionamento;
2. screenshot ou GIF do dashboard;
3. problema que o projeto resolve;
4. arquitetura resumida;
5. fluxo dos dados;
6. tecnologias utilizadas;
7. instruções de execução;
8. exemplo de teste ponta a ponta;
9. métricas dos modelos;
10. limitações e próximos passos;
11. licença e fontes dos datasets.

Substituir instruções genéricas como `<seu-repositorio>` pelo endereço real do GitHub.

### 3.2 Corrigir consistência do texto

Antes da publicação, verificar se todos os arquivos descrevem a mesma configuração. A documentação menciona `insurance_claims` em alguns lugares, enquanto o `docker-compose.yml` usa `creditcard_transactions`. Escolher uma estratégia:

- documentar claramente os dois pipelines; ou
- deixar um dataset como fluxo principal e marcar o outro como experimento.

Também revisar referências antigas como `worker-insurance` e nomes de serviços que não existem mais. **Resultado atual:** o README foi alinhado ao worker `worker-worker_transactions`, ao profile `seed` e aos 11 serviços principais do Compose.

### 3.3 Revisar segurança

- [ ] Remover senhas reais, e-mails pessoais e tokens. **Pendente:** ainda existem valores de senha no `docker-compose.yml`; são aparentemente locais, mas precisam ser confirmados.
- [x] Manter apenas valores fictícios em arquivos de exemplo. `.env.example` usa e-mails genéricos.
- [x] Usar `.env.example` para configuração local.
- [ ] Explicar no README que as credenciais do Compose são somente para desenvolvimento.
- [x] Confirmar que `.env`, modelos locais e arquivos CSV privados estão ignorados pelo Git. O `.gitignore` cobre `.env`, CSVs, cache e modelos; os CSVs de seed são versionados intencionalmente.
- [ ] Procurar por senhas antes do push:

```powershell
rg -n -i "password|senha|secret|token|api.?key|gmail|@" --glob "!*.lock" --glob "!*.csv"
```

Se alguma credencial real já tiver sido publicada, revogá-la e substituí-la. Apagar o texto de um commit atual não é suficiente.

## 4. Fase 2: validar o fluxo completo

Executar a validação na ordem abaixo e guardar evidências.

### 4.1 Testes automatizados

```powershell
pytest -q
```

Registrar:

- quantidade de testes;
- quantidade de testes aprovados;
- falhas corrigidas;
- limitações ainda existentes.

### 4.2 Validação da configuração

```powershell
docker compose config
```

Depois subir o ambiente:

```powershell
docker compose up --build -d

docker compose ps
```

Verificar:

- frontend;
- backend e Swagger;
- Kafka UI;
- Kafka Connect;
- PostgreSQL de origem;
- PostgreSQL interno;
- detector;
- handler.

### 4.3 Demonstração ponta a ponta

**Resultado da auditoria atual:** o seed automatizado executou com sucesso, criou o tópico `source-postgres.public.creditcard_transactions`, registrou a pipeline como ativa e produziu 112 alertas em `anomalies_history`. A revisão pela API marcou 104 como `confirmed_fraud` e 8 como `false_positive`; a API de estatísticas retornou precision de 92,9% e zero pendentes. A demonstração visual foi capturada e o diagrama foi validado: ele representa tanto a persistência de metadados do Detector quanto o fluxo de alertas pelo tópico `detected_anomalies`.

Criar um roteiro determinístico:

1. subir os containers;
2. executar o seed;
3. confirmar a criação do evento no Kafka;
4. confirmar que o detector consumiu o evento;
5. confirmar que o handler persistiu o alerta;
6. abrir o dashboard;
7. alterar o alerta para `confirmed_fraud` ou `false_positive`;
8. capturar a tela e os logs relevantes.

Não usar dados pessoais ou transações reais na demonstração.

## 5. Fase 3: testar o dataset atual

O primeiro dataset recomendado é o de fraude em cartão, porque já está integrado ao fluxo principal e possui rótulo de fraude para avaliação supervisionada.

Registrar em uma tabela:

| Item | Resultado |
|---|---|
| Quantidade total de registros | preencher |
| Quantidade de fraudes | 492 inseridas pelo seed; modelo treinado apenas com dados normais |
| Percentual de fraude | preencher |
| Colunas usadas | preencher |
| Colunas ignoradas | preencher |
| Precision | 92,86% offline; dashboard exibe 92,9% após a revisão |
| Recall | 21,14% offline: 104 das 492 fraudes foram detectadas |
| F1-score | 34,44% offline |
| Falsos positivos | 8 offline; dashboard exibe 8 após a revisão |
| Tempo aproximado de processamento | seed concluído em aproximadamente 16 segundos nesta execução |

O registro do modelo confirmou `samples: 15000`, `fraud_count: 0`, `labeled_data: 0`, `feature_count: 30` e `rf_model_trained: false`. A validação offline cruzou os 112 IDs dos alertas com a coluna `Class` do CSV, respeitando a reordenação de IDs feita pelo seed: 104 verdadeiros positivos, 8 falsos positivos e 388 falsos negativos.

Essas métricas são do experimento executado com o seed e não devem ser chamadas de métricas de produção. Para o dashboard refletir esses números, os alertas precisam ser revisados e receber os status corretos.

Não usar somente acurácia. Como as classes são desbalanceadas, precision, recall, F1-score e matriz de confusão são mais informativos.

### Evidências coletadas e pendentes

- [x] Seed concluído com 15.000 registros normais e 492 fraudes.
- [x] Pipeline registrada como `active`, com modelo `v001`.
- [x] Tópico CDC criado e confirmado com 15.492 mensagens processáveis.
- [x] Interfaces frontend, Swagger, Kafka UI e Kafka Connect responderam com HTTP 200.
- [x] Saída da validação offline dos alertas.
- [x] Matriz de confusão derivada do cruzamento com o CSV: TP 104, FP 8, FN 388; TN 14.992.
- [ ] Valores dos thresholds relacionados a um resultado avaliado.
- [x] Quantidade de anomalias geradas: 112 alertas pendentes.
- [x] Screenshot do dashboard com os alertas revisados foi obtido.
- [ ] Screenshot do tópico de anomalias.
- [ ] Versão do modelo e data do treinamento. **Parcial:** `v001` foi registrado; falta reunir isso com as métricas.

## 6. Fase 4: decidir se vale testar outro dataset

Testar outro dataset é útil para demonstrar generalização, mas não deve atrasar a primeira publicação. Fazer o segundo experimento somente depois que o dataset principal estiver reproduzível.

### Regra de decisão

Publicar o segundo dataset como resultado principal apenas se:

- o pipeline executar sem alterações manuais escondidas;
- o modelo tiver métricas calculadas em conjunto de teste separado;
- o fluxo de eventos chegar ao dashboard;
- as diferenças entre os datasets estiverem documentadas.

Caso contrário, apresentá-lo como trabalho futuro ou experimento parcial.

### Verificação do fluxo do dataset principal

O seed insere as linhas fraudulentas após o treinamento e a execução atual gerou 112 linhas em `anomalies_history`. A revisão pela API confirmou 104 fraudes e 8 falsos positivos. O Detector persiste metadados em `pipelines_config` e `model_versions`, e o Handler persiste os alertas em `anomalies_history`. As verificações realizadas foram:

1. confirmar que o consumidor do detector está no grupo e tópico corretos;
2. confirmar que os eventos das 492 fraudes foram consumidos após a ativação do modelo;
3. verificar o score do Isolation Forest e a decisão dos thresholds;
4. verificar se o detector publica o tópico de anomalias;
5. verificar se o handler está inscrito nesse tópico;
6. verificar a gravação em `anomalies_history`;
7. repetir a consulta da API depois da persistência.

Critério de fluxo validado: pelo menos um alerta produzido pelo evento de fraude, persistido no banco interno e retornado por `GET /api/anomalies`.

## 7. Fase 5: melhorar a documentação de Machine Learning

Completar `docs/Model_Documentation.md` com:

- por que usar Isolation Forest;
- por que usar Random Forest;
- como funciona a combinação dos modelos;
- como os thresholds são escolhidos;
- como o desbalanceamento é tratado;
- como os dados são separados em treino e teste;
- métricas obtidas;
- exemplos de falsos positivos e verdadeiros positivos;
- como disparar o retreinamento;
- limitações do dataset;
- risco de vazamento de dados;
- diferença entre anomalia estatística e fraude confirmada.

Não apresentar o modelo como capaz de provar fraude. O sistema identifica casos para investigação.

## 8. Materiais visuais

Preparar os seguintes arquivos:

- [ ] diagrama atualizado da arquitetura. O arquivo existe, mas ainda falta conferir sua correspondência com o Compose atual;
- [x] screenshot do dashboard sem dados sensíveis;
- [ ] screenshot da documentação Swagger;
- [ ] screenshot do Kafka UI mostrando um evento;
- [ ] gráfico de precision, recall e F1-score;
- [ ] vídeo de 30 a 60 segundos mostrando uma transação entrando e o alerta aparecendo;
- [ ] imagem de capa para o post.

### Estrutura sugerida para o carrossel

1. **Capa:** Plataforma de detecção de anomalias com Machine Learning
2. **Problema:** como identificar eventos suspeitos em um fluxo de dados
3. **Arquitetura:** PostgreSQL -> Debezium -> Kafka -> Detector -> Handler -> Dashboard
4. **Modelos:** Isolation Forest + Random Forest e thresholds configuráveis
5. **Resultado:** métricas e exemplo de alerta
6. **Aprendizados:** streaming, confiabilidade, persistência e retreinamento
7. **Código:** link para o GitHub e próximos passos

Usar pouco texto por imagem. O detalhe técnico deve ficar no texto do post ou no README.

## 9. Sequência de publicações

### Publicação 1: apresentação do projeto

Objetivo: gerar interesse e explicar o que foi construído.

Texto-base:

> Construí uma plataforma de detecção de anomalias para dados de transações.
>
> O fluxo captura alterações em um PostgreSQL, publica os eventos usando Debezium e Kafka, aplica modelos de Machine Learning e disponibiliza os alertas em um dashboard web.
>
> Tecnologias utilizadas: Python, Scikit-learn, FastAPI, React, PostgreSQL, Kafka, Debezium e Docker.
>
> O projeto me permitiu estudar não apenas os modelos, mas também os problemas de integração entre streaming, persistência, retreinamento e tratamento de falhas.
>
> O código e a documentação estão disponíveis aqui: [link]
>
> #Python #MachineLearning #DataEngineering #Kafka #MLOps

Anexar o carrossel ou uma imagem forte do dashboard.

### Publicação 2: arquitetura e engenharia de dados

Objetivo: mostrar profundidade técnica.

Explicar o fluxo de eventos, o papel do CDC, os consumidores, os offsets, a persistência e o tratamento dos alertas.

Começar com uma pergunta, por exemplo:

> O que acontece depois que uma transação é inserida no banco?

Anexar o diagrama e, se possível, o vídeo do fluxo.

### Publicação 3: modelos e resultados

Objetivo: mostrar que houve avaliação e não apenas integração de ferramentas.

Explicar:

- qual é a função de cada modelo;
- como os thresholds foram definidos;
- quais métricas foram observadas;
- quais são as limitações;
- por que um alerta precisa de revisão humana.

Anexar a matriz de confusão e os números reais do experimento.

### Publicação 4: aprendizados e próximos passos

Objetivo: mostrar maturidade técnica.

Falar sobre:

- o que foi mais difícil;
- quais decisões mudaram durante o desenvolvimento;
- como os testes ajudaram;
- o que ainda falta para produção;
- próximos passos: CI/CD, observabilidade, health checks, logs estruturados e deploy em cloud.

## 10. Estrutura final do README

Usar esta ordem:

```text
Título e resumo
Screenshot
Problema
Arquitetura
Fluxo dos dados
Tecnologias
Como executar
Como gerar uma anomalia
Como avaliar os modelos
Métricas
Estrutura do projeto
Limitações
Roadmap
Fontes dos datasets
Licença
```

O README deve levar o leitor até uma demonstração funcional rapidamente. A documentação detalhada de modelos deve permanecer em `docs/Model_Documentation.md`.

## 11. Checklist final antes do push

- [ ] O repositório tem nome e descrição claros.
- [ ] O README foi revisado por alguém que não conhece o projeto.
- [ ] O comando de instalação foi testado do zero.
- [ ] `pytest -q` passou.
- [ ] `docker compose config` passou.
- [ ] O dashboard foi testado.
- [ ] As métricas são reais e reproduzíveis.
- [ ] Os datasets têm fonte e licença indicadas.
- [ ] Senhas e dados pessoais foram removidos.
- [ ] O diagrama corresponde ao código atual.
- [ ] O vídeo não mostra terminais com credenciais.
- [ ] O link do GitHub funciona.
- [ ] O post não usa termos como “produção”, “100% confiável” ou “prevê fraudes” sem evidência.

## 12. Ordem recomendada de execução

1. Corrigir segurança e inconsistências do README.
2. Fazer o dataset de cartão funcionar de ponta a ponta.
3. Medir e registrar as métricas.
4. Completar a documentação dos modelos.
5. Criar screenshots, diagrama e vídeo.
6. Atualizar o README com o caminho reproduzível.
7. Testar o segundo dataset, se ainda houver tempo e se ele demonstrar uma capacidade nova.
8. Publicar o primeiro post.
9. Publicar os posts técnicos em intervalos de alguns dias.
10. Atualizar o projeto conforme surgirem comentários e perguntas.

## Resultado esperado

Ao final, o leitor deve conseguir responder rapidamente:

- qual problema o projeto resolve;
- como os dados percorrem o sistema;
- quais tecnologias foram usadas;
- o que os modelos fazem;
- quais resultados foram obtidos;
- como executar uma demonstração;
- o que ainda falta para levar a solução a produção.
