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

    #Encontrar o limiar ideal do random forest isolado na validaçao
    best_rf_threshold = 0.5
    best_rf_f1 = -1
    
    for thresh in np.linspace(0.1, 0.9, 81):
        pred_val_rf = (y_rf_proba_val >= thresh).astype(int)
        f1_rf_val = f1_score(y_val, pred_val_rf, zero_division=0)
        if f1_rf_val > best_rf_f1:
            best_rf_f1 = f1_rf_val
            best_rf_threshold = thresh

    print(f"Melhor limiar encontrado para o Random Forest na Validação: {best_rf_threshold:.4f} (F1: {best_rf_f1:.4f})")

    #faz a calibragem das regras hibridas
    best_f1 = -1.0
    best_config = None
    rf_high_candidates = np.linspace(0.4, max(0.7, y_rf_proba_val.max()), 12)
    rf_mod_candidates = np.linspace(0.1, 0.4, 7)
    if_comb_candidates = np.linspace(scores_if_val.min(), min(-0.001, scores_if_val.max()), 7)
    if_stand_candidates = np.linspace(scores_if_val.min(), min(-0.001, scores_if_val.max()), 7)

    for rf_high in rf_high_candidates:
        for rf_mod in rf_mod_candidates:
            if rf_mod >= rf_high:
                continue
            for if_comb in if_comb_candidates:
                for if_stand in if_stand_candidates:
                    pred_val = np.zeros(len(X_val_scaled), dtype=int)
                    rule_high = y_rf_proba_val >= rf_high
                    rule_moderate = (y_rf_proba_val >= rf_mod) & (y_rf_proba_val < rf_high)
                    rule_if_combined = scores_if_val < if_comb
                    rule_if_standalone = scores_if_val < if_stand
                    
                    pred_val[rule_high] = 1
                    pred_val[(rule_moderate & rule_if_combined) | rule_if_standalone] = 1
                    
                    f1 = f1_score(y_val, pred_val, pos_label=1, zero_division=0)
                    if f1 > best_f1:
                        best_f1 = f1
                        best_config = (rf_high, rf_mod, if_comb, if_stand)

    if best_config is None:
        best_config = (0.85, 0.4, -0.15, -0.1)

    RF_HIGH_CONFIDENCE_THRESHOLD, RF_MODERATE_THRESHOLD, IF_COMBINED_THRESHOLD, IF_STANDALONE_THRESHOLD = best_config

    print('\nMelhores Limiares encontrados na Validação para o Híbrido:')
    print(f'  RF Limiar Alto: {RF_HIGH_CONFIDENCE_THRESHOLD:.4f}')
    print(f'  RF Limiar Moderado: {RF_MODERATE_THRESHOLD:.4f}')
    print(f'  IF Combinado: {IF_COMBINED_THRESHOLD:.4f}')
    print(f'  IF Standalone: {IF_STANDALONE_THRESHOLD:.4f}')
    print(f'  Best Hybrid Validation F1: {best_f1:.4f}\n')


    # ---------------------
    # 5. AVALIAÇÃO FINAL NO CONJUNTO DE TESTE (Dados nunca antes vistos)
    # ---------------------
    # Predição Isolation Forest no Teste
    y_if_pred_test = isolation_forest.predict(X_test_scaled)
    y_if_test = np.where(y_if_pred_test == -1, 1, 0)

    # Predição Random Forest no Teste (Usando o melhor limiar descoberto na validação)
    y_rf_pred_test = (y_rf_proba_test >= best_rf_threshold).astype(int)

    # Predição Modelo Híbrido no Teste
    hybrid_pred_test = np.zeros(len(X_test_scaled), dtype=int)
    rule_high_test = y_rf_proba_test >= RF_HIGH_CONFIDENCE_THRESHOLD
    rule_mod_test = (y_rf_proba_test >= RF_MODERATE_THRESHOLD) & (y_rf_proba_test < RF_HIGH_CONFIDENCE_THRESHOLD)
    rule_if_comb_test = scores_if_test < IF_COMBINED_THRESHOLD
    rule_if_stand_test = scores_if_test < IF_STANDALONE_THRESHOLD

    hybrid_pred_test[rule_high_test] = 1
    hybrid_pred_test[(rule_mod_test & rule_if_comb_test) | rule_if_stand_test] = 1

    # Métricas de cálculo
    def calculate_metrics(y_real, y_pred):
        return (
            precision_score(y_real, y_pred, pos_label=1, zero_division=0),
            recall_score(y_real, y_pred, pos_label=1, zero_division=0),
            f1_score(y_real, y_pred, pos_label=1, zero_division=0),
        )

    def count_anomalies(y_real, y_pred):
        tp = int(((y_real == 1) & (y_pred == 1)).sum())
        fn = int(((y_real == 1) & (y_pred == 0)).sum())
        fp = int(((y_real == 0) & (y_pred == 1)).sum())
        tn = int(((y_real == 0) & (y_pred == 0)).sum())
        return tp, fn, fp, tn

    prec_if, rec_if, f1_if = calculate_metrics(y_test, y_if_test)
    prec_rf, rec_rf, f1_rf = calculate_metrics(y_test, y_rf_pred_test)
    prec_hy, rec_hy, f1_hy = calculate_metrics(y_test, hybrid_pred_test)

    tp_if, fn_if, fp_if, tn_if = count_anomalies(y_test, y_if_test)
    tp_rf, fn_rf, fp_rf, tn_rf = count_anomalies(y_test, y_rf_pred_test)
    tp_hy, fn_hy, fp_hy, tn_hy = count_anomalies(y_test, hybrid_pred_test)

    print('Exact anomaly counts (on isolated test set):')
    print(f'  Isolation Forest caught {tp_if} frauds, missed {fn_if}, false positives {fp_if}')
    print(f'  Random Forest caught {tp_rf} frauds, missed {fn_rf}, false positives {fp_rf}')
    print(f'  Hybrid model caught {tp_hy} frauds, missed {fn_hy}, false positives {fp_hy}')

    df_compare = pd.DataFrame({
        'Model': ['Isolation Forest', 'Random Forest', 'Hybrid (IF + RF)'],
        'Precision': [prec_if, prec_rf, prec_hy],
        'Recall': [rec_if, rec_rf, rec_hy],
        'F1-Score': [f1_if, f1_rf, f1_hy],
    })

    print('\n' + '=' * 70)
    print('Performance comparison on credit card dataset (Test Set):')
    print(df_compare.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
    print('=' * 70)
    sys.stdout.flush()