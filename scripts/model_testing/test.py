import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split


# 1. Altere o caminho para onde salvou o seu dataset de cartão de crédito
DATASET_RELATIVE_PATH = 'C:\\Users\\augusto.hagemeier\\Documents\\almoço\\database_anomalies\\scripts\\startup_datasets_seed\\creditcard_small.csv'

if __name__ == '__main__':
    csv_path = os.path.abspath(DATASET_RELATIVE_PATH)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)
    
    # No dataset de cartão de crédito, o alvo chama-se 'Class' (0 = normal, 1 = fraude)
    target_col = 'Class'

    if target_col not in df.columns:
        raise ValueError(f"Expected target column '{target_col}' not found in dataset")

    print(f"Loaded dataset: {csv_path}")
    print(f"Total rows: {len(df)}")
    print(f"Fraud rows: {(df[target_col] == 1).sum()}")
    print(f"Normal rows: {(df[target_col] == 0).sum()}")
    print(f"Fraud ratio: {df[target_col].mean():.4f}\n")

    # A coluna 'Time' indica apenas os segundos decorridos e não agrega valor preditivo
    drop_cols = [target_col, 'Time']
    X_raw = df.drop(columns=drop_cols, errors='ignore')
    y = df[target_col].astype(int)

    # Criando o dataset de teste e separando entre treino, calibração do hibrido, e test
    # aqui separamos o dataset de teste com 20% e sobra 60% dos dados para a próxima divisão
    X_train_full, X_test,y_train_full,y_test = train_test_split(
        X_raw,y,test_size=.2, stratify=y,random_state=42
    )
    #aqui eu pego 80% dos dados restantes e separo 25% de 80% que sobrou para ficar 20 como val e sobrar 60 como dados de treino
    X_train,X_val,y_train,y_val = train_test_split(
        X_train_full,y_train_full,test_size=.25,stratify=y,random_state=42
    )

    #Aqui fazemos o escalonamento dos dados, para garantir que todas as features tem o mesmo peso para os modelos
    scaler = StandardScaler()
    #Aqui usamos o fit_transform para ele fazer a média e o desvio padrão para conseguir achatar a distribuição das variáveis
    X_train_scaled = scaler.fit_transform(X_train)
    #Aqui só o transform para o modelo utilizar somente o que ele já aprender com o fit transform da linha de cima e não deixar vazar dados
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    ##Isolation Forest
    contamination_rate = max(0.01,y_train.mean())
    
    isolation_forest = IsolationForest(
        contamination=contamination_rate,
        random_state=42,
        n_estimatores=200           #Constroi 200 arvores de isolamento para melhorar o resultado
    )

    isolation_forest.fit(X_train_scaled)

    ##Random Forest
    model_rf = RandomForestClassifier(
        n_estimators=150,           # número de arvores na floresta, no final o modelo faz uma votação entre 150 arvores para dar a resposta
        random_state=42,            
        n_jobs=-1,                  # instrui a utilizar todos os nucleos disponiveis de forma paralela
        class_weight='balanced',    # esse parametro serve para o desbalanceamento, com 97% das transações normais e 3% fraudes. 
                                    # Esse parametro faz com que o modelo evite ignorar fraudes para manter acuracia

        max_depth=12,               # Garante que a profundidade seja de no máximo 12 niveis, evita que a arvore decore o treino
        min_samples_leaf=2          # Mínimo de amostras na folha, para garantir que ele aprenda regras robustas
    )

    model_rf.fit(X_train_scaled,y_train)


    #Pegando as probabilidades para os modelos híbridos
    #Aqui pega as previsões para a validação e os testes
    y_rf_proba_val = model_rf.predict_proba(X_val_scaled)[:,1]
    y_rf_proba_test = model_rf.predict_proba(X_test_scaled)[:,1]

    #Pega os scores do IF para a validação e teste
    scores_if_val = isolation_forest.decision_function(X_val_scaled)
    scores_if_test = isolation_forest.decision_function(X_test_scaled)


