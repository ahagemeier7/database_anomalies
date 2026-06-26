import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import confusion_matrix, classification_report, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

DATASET_RELATIVE_PATH = os.path.join('scripts', 'startup_datasets_seed', 'insurance_fraud.csv')

if __name__ == '__main__':
    csv_path = os.path.abspath(DATASET_RELATIVE_PATH)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)
    target_col = 'FraudFound_P'

    if target_col not in df.columns:
        raise ValueError(f"Expected target column '{target_col}' not found in dataset")

    print(f"Loaded dataset: {csv_path}")
    print(f"Total rows: {len(df)}")
    print(f"Fraud rows: {(df[target_col] == 1).sum()}")
    print(f"Normal rows: {(df[target_col] == 0).sum()}")
    print(f"Fraud ratio: {df[target_col].mean():.4f}\n")

    # Remove columns that are identifiers or not meaningful for modeling
    drop_cols = [target_col, 'PolicyNumber', 'RepNumber']
    X_raw = df.drop(columns=drop_cols, errors='ignore')
    y = df[target_col].astype(int)

    for col in X_raw.columns:
        if X_raw[col].dtype == object:
            coerced = pd.to_numeric(X_raw[col], errors='coerce')
            if coerced.notna().all():
                X_raw[col] = coerced

    X_dict = X_raw.to_dict(orient='records')
    vectorizer = DictVectorizer(sparse=False)
    X_vectorized = vectorizer.fit_transform(X_dict)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_vectorized)

    # ---------------------
    # Isolation Forest
    # ---------------------
    isolation_forest = IsolationForest(contamination=0.01, random_state=42)
    isolation_forest.fit(X_scaled)

    y_if_pred_raw = isolation_forest.predict(X_scaled)
    y_if_pred = np.where(y_if_pred_raw == -1, 1, 0)

    print('Isolation Forest performance:')
    print(classification_report(y, y_if_pred, target_names=['Normal', 'Fraud'], zero_division=0))

    cm_if = confusion_matrix(y, y_if_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_if, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Pred Normal', 'Pred Fraud'],
                yticklabels=['True Normal', 'True Fraud'])
    plt.title('Isolation Forest Confusion Matrix')
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.show()

    df_if_scores = pd.DataFrame({'Score_Anomaly': isolation_forest.decision_function(X_scaled), target_col: y})
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_if_scores, x='Score_Anomaly', hue=target_col, bins=50, kde=True,
                 palette={0: 'blue', 1: 'red'})
    plt.title('Isolation Forest Anomaly Score Distribution')
    plt.show()

    # ---------------------
    # Random Forest supervised model
    # ---------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled,
        y,
        test_size=0.3,
        stratify=y,
        random_state=42,
    )

    model_rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model_rf.fit(X_train, y_train)

    y_rf_pred = model_rf.predict(X_test)
    y_rf_proba = model_rf.predict_proba(X_test)[:, 1]

    print('\nRandom Forest performance:')
    print(classification_report(y_test, y_rf_pred, target_names=['Normal', 'Fraud'], zero_division=0))

    cm_rf = confusion_matrix(y_test, y_rf_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_rf, annot=True, fmt='d', cmap='Greens',
                xticklabels=['Pred Normal', 'Pred Fraud'],
                yticklabels=['True Normal', 'True Fraud'])
    plt.title('Random Forest Confusion Matrix')
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.show()

    df_rf_prob = pd.DataFrame({'FraudProbability': y_rf_proba, target_col: y_test.reset_index(drop=True)})
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_rf_prob, x='FraudProbability', hue=target_col, bins=50, kde=True,
                 palette={0: 'blue', 1: 'red'})
    plt.title('Random Forest Fraud Probability Distribution')
    plt.xlabel('Probability of Fraud')
    plt.show()

    # ---------------------
    # Hybrid evaluation using worker thresholds
    # ---------------------
    RF_HIGH_CONFIDENCE_THRESHOLD = 0.85
    RF_MODERATE_THRESHOLD = 0.4
    IF_COMBINED_THRESHOLD = -0.15
    IF_STANDALONE_THRESHOLD = -0.1

    scores_if_test = isolation_forest.decision_function(X_test)
    hybrid_pred = np.zeros(len(X_test), dtype=int)

    rule_high = y_rf_proba >= RF_HIGH_CONFIDENCE_THRESHOLD
    rule_moderate = (y_rf_proba >= RF_MODERATE_THRESHOLD) & (y_rf_proba < RF_HIGH_CONFIDENCE_THRESHOLD)
    rule_if_combined = scores_if_test < IF_COMBINED_THRESHOLD
    rule_if_standalone = scores_if_test < IF_STANDALONE_THRESHOLD

    hybrid_pred[rule_high] = 1
    hybrid_pred[(rule_moderate & rule_if_combined) | rule_if_standalone] = 1

    print('\nHybrid performance (worker thresholds):')
    print(f'  RF high confidence >= {RF_HIGH_CONFIDENCE_THRESHOLD}')
    print(f'  RF moderate >= {RF_MODERATE_THRESHOLD} and IF < {IF_COMBINED_THRESHOLD}')
    print(f'  IF standalone < {IF_STANDALONE_THRESHOLD}')
    print(classification_report(y_test, hybrid_pred, target_names=['Normal', 'Fraud'], zero_division=0))

    cm_hybrid = confusion_matrix(y_test, hybrid_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_hybrid, annot=True, fmt='d', cmap='Purples',
                xticklabels=['Pred Normal', 'Pred Fraud'],
                yticklabels=['True Normal', 'True Fraud'])
    plt.title('Hybrid IF + RF Confusion Matrix')
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.show()

    # ---------------------
    # Final comparison
    # ---------------------
    def calculate_metrics(y_real, y_pred):
        return (
            precision_score(y_real, y_pred, pos_label=1, zero_division=0),
            recall_score(y_real, y_pred, pos_label=1, zero_division=0),
            f1_score(y_real, y_pred, pos_label=1, zero_division=0),
        )

    y_if_test = np.where(scores_if_test < 0, 1, 0)
    prec_if, rec_if, f1_if = calculate_metrics(y_test, y_if_test)
    prec_rf, rec_rf, f1_rf = calculate_metrics(y_test, y_rf_pred)
    prec_hy, rec_hy, f1_hy = calculate_metrics(y_test, hybrid_pred)

    df_compare = pd.DataFrame({
        'Model': ['Isolation Forest', 'Random Forest', 'Hybrid (IF + RF)'],
        'Precision': [prec_if, prec_rf, prec_hy],
        'Recall': [rec_if, rec_rf, rec_hy],
        'F1-Score': [f1_if, f1_rf, f1_hy],
    })

    print('\n' + '=' * 70)
    print('Performance comparison on insurance claims dataset:')
    print(df_compare.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
    print('=' * 70)

    comparison_melted = df_compare.melt(id_vars='Model', var_name='Metric', value_name='Score')
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(data=comparison_melted, x='Metric', y='Score', hue='Model', palette='magma')
    plt.ylim(0, 1.0)
    plt.title('Model Performance Comparison')
    plt.legend(title='Model')
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(f'{height:.2f}',
                        (p.get_x() + p.get_width() / 2., height),
                        ha='center', va='center', xytext=(0, 8), textcoords='offset points', fontsize=9)
    plt.show()
