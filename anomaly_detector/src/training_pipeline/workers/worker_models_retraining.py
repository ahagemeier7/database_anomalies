import os
import json
import logging
import joblib
import pandas as pd
from dotenv import load_dotenv
from training_pipeline.db.db_internal import get_db_engine as get_db_engine_iternal
from training_pipeline.db.db_source import get_db_engine as get_db_engine_source
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retrain_hybrid_models(target_table: str, columns_to_ignore: list = None) -> None:

  contamination = float(os.getenv("CONTAMINATION"))

  engine_source = get_db_engine_source()
  engine_internal = get_db_engine_iternal()

  try:
    df_source = pd.read_sql(f"SELECT * FROM {target_table}", engine_source)
    df_source['is_fraud'] = 0

    logging.info("Buscando histórico de auditoria no banco interno...")
    query_internal = f"""
            SELECT 
                raw_event->>'id' AS original_id, 
                status 
            FROM anomalies_history 
            WHERE origin_table = '{target_table}' 
            AND status IN ('confirmed_fraud', 'false_positive')
        """
    df_history = pd.read_sql(query_internal, engine_internal)
    
    if not df_history.empty:
      df_history['original_id'] = df_history['original_id'].astype(df_source['id'].dtype)
      
      frauds_ids = df_history[df_history['status'] == 'confirmed_fraud']['original_id']
      false_pos_ids = df_history[df_history['status'] == 'false_positive']['original_id']

      df_source.loc[df_source['id'].isin(frauds_ids), 'is_fraud'] = 1
      df_source.loc[df_source['id'].isin(false_pos_ids), 'is_fraud'] = 0
    else:
      logging.info('No data verified found')

    columns_to_drop = columns_to_ignore.copy() if columns_to_ignore else []
    columns_to_drop.extend(['is_fraud', 'Class'])

    df_features = df_source.drop(columns=columns_to_drop, errors='ignore')

    for col in df_features.columns:
      df_features[col] = pd.to_numeric(df_features[col], errors='ignore')

    # Convert dates to string to work with dict vectorizer
    for col in df_features.columns:
        if pd.api.types.is_datetime64_any_dtype(df_features[col]):
            df_features[col] = df_features[col].astype(str)

    data_dict = df_features.to_dict(orient='records')

    translator = DictVectorizer(sparse=False)

    X = translator.fit_transform(data_dict)

    # Scale features — IsolationForest is sensitive to feature scale.
    # StandardScaler ensures all numeric features contribute equally
    # to the anomaly score, preventing large-range columns from dominating.
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    y = df_source['is_fraud']

    i_forest = IsolationForest(contamination=contamination,random_state=42)
    i_forest.fit(X)

    rf_trained = False

    if not df_history.empty and 1 in y.values:
      labeled_ids = df_history['original_id'].unique()
      labeled_mask = df_source['id'].isin(labeled_ids)
      X_labeled = X[labeled_mask]
      y_labeled = y[labeled_mask].values

      if 1 in y_labeled:
        # Split into train/test to evaluate model performance
        X_train, X_test, y_train, y_test = train_test_split(
            X_labeled, y_labeled, test_size=0.2, stratify=y_labeled, random_state=42
        )

        r_forest = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        r_forest.fit(X_train, y_train)

        y_pred = r_forest.predict(X_test)
        logging.info(
            f"Random Forest validation (test set: {len(y_test)} samples):\n"
            f"{classification_report(y_test, y_pred, zero_division=0)}"
        )

        # Retrain on the full labeled set for the final saved model
        r_forest.fit(X_labeled, y_labeled)
        rf_trained = True
        logging.info(f"Random Forest final model trained on {len(y_labeled)} labeled rows "
                     f"({(y_labeled == 1).sum()} frauds, {(y_labeled == 0).sum()} false positives)")
      else:
        logging.warning('No confirmed fraud in labeled data, skipping random forest')
    else:
      logging.warning('No labeled data available, skipping random forest')

    models_dir = os.path.join(os.getcwd(), 'models')
    os.makedirs(models_dir, exist_ok=True)

    translator_path = os.path.join(models_dir, f'{target_table}_translator.pkl')
    if_model_path = os.path.join(models_dir, f'{target_table}_if_model.pkl')
    rf_model_path = os.path.join(models_dir, f'{target_table}_rf_model.pkl')
    scaler_path = os.path.join(models_dir, f'{target_table}_scaler.pkl')

    joblib.dump(translator, translator_path)
    joblib.dump(i_forest, if_model_path)
    joblib.dump(scaler, scaler_path)
        
    if rf_trained:
      joblib.dump(r_forest, rf_model_path)
    else:
      logging.info(f"Isolation Forest saved in {models_dir}")

  except Exception as e:
    logging.error(f"Critical error during model retrain {e}")
    raise 