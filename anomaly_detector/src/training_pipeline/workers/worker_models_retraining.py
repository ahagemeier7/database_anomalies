import os
import json
import logging
import joblib
import pandas as pd
from dotenv import load_dotenv
from src.training_pipeline.db.db_internal import get_db_engine as get_db_engine_iternal
from src.training_pipeline.db.db_source import get_db_engine as get_db_engine_source
from sqlalchemy import text
from src.training_pipeline.workers.model_versioning import (
    save_versioned_models,
    insert_model_version_record,
)
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retrain_hybrid_models(target_table: str, columns_to_ignore: list = None) -> None:

  contamination = float(os.getenv("CONTAMINATION", "0.01"))

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
    r_forest = None
    rf_metrics = {}  # Will hold precision/recall/f1 if we can compute them

    if not df_history.empty and 1 in y.values:
      labeled_ids = df_history['original_id'].unique()
      labeled_mask = df_source['id'].isin(labeled_ids)
      X_labeled = X[labeled_mask]
      y_labeled = y[labeled_mask].values

      if 1 in y_labeled:
        # Ensure we have enough samples for a stratified split
        unique_classes = set(y_labeled)
        min_samples_per_class = min((y_labeled == c).sum() for c in unique_classes)

        if min_samples_per_class >= 2:
          # Enough samples — split, validate, then retrain on full set
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

          rf_metrics = {
            "training_samples": int(len(y_labeled)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
          }

          # Retrain on the full labeled set for the final saved model
          r_forest.fit(X_labeled, y_labeled)
          rf_trained = True
          logging.info(f"Random Forest final model trained on {len(y_labeled)} labeled rows "
                       f"({(y_labeled == 1).sum()} frauds, {(y_labeled == 0).sum()} false positives)")
        else:
          # Not enough samples for a split — train on all labeled data without validation
          logging.warning(
            f"Not enough labeled samples per class ({min_samples_per_class}) for train/test split. "
            "Using all labeled data for training."
          )
          r_forest = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
          r_forest.fit(X_labeled, y_labeled)
          rf_trained = True
          rf_metrics = {
            "training_samples": int(len(y_labeled)),
          }
          logging.info(f"Random Forest final model trained on {len(y_labeled)} labeled rows "
                       f"({(y_labeled == 1).sum()} frauds, {(y_labeled == 0).sum()} false positives)")
      else:
        logging.warning('No confirmed fraud in labeled data, skipping random forest')
    else:
      logging.warning('No labeled data available, skipping random forest')

    models_dir = os.path.join(os.getcwd(), 'models')
    model_metadata = save_versioned_models(
        target_table=target_table,
        models_dir=models_dir,
        translator=translator,
        isolation_forest=i_forest,
        scaler=scaler,
        rf_model=r_forest if rf_trained else None,
    )

    metrics = {
      "samples": int(len(df_source)),
      "feature_count": int(df_features.shape[1]),
      "rf_model_trained": rf_trained,
      "labeled_data": int(len(df_history)) if not df_history.empty else 0,
      "fraud_count": int((y == 1).sum()),
    }
    metrics.update(rf_metrics)

    insert_model_version_record(
      engine_internal,
      target_table,
      model_metadata["version"],
      model_metadata["paths"],
      metrics=metrics,
      is_active=True,
    )

    # Automatically activate this new version in pipelines_config
    version_tag = model_metadata["version"]
    with engine_internal.connect() as conn:
      conn.execute(
        text("UPDATE model_versions SET is_active = false WHERE target_table = :target_table AND version != :version"),
        {"target_table": target_table, "version": version_tag}
      )
      conn.execute(
        text("UPDATE pipelines_config SET active_model_version = :version WHERE target_table = :target_table"),
        {"target_table": target_table, "version": version_tag}
      )
      conn.commit()

    logging.info("New model version %s activated for table '%s'.", version_tag, target_table)

  except Exception as e:
    logging.error(f"Critical error during model retrain {e}")
    raise