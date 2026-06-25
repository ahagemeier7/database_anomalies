import os
import logging
import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from src.training_pipeline.db.db_internal import get_db_engine as get_db_engine_internal
from src.training_pipeline.db.db_source import get_db_engine
from src.training_pipeline.workers.model_versioning import save_versioned_models, insert_model_version_record
import pandas as pd


def train_models(target_table: str,columns_to_ignore:list = None) -> None:

  contamination = float(os.getenv("CONTAMINATION", "0.01"))

  #fetching DB data
  try:
    engine = get_db_engine()

    df = pd.read_sql(f"SELECT * FROM {target_table}", engine)
  except Exception as e:
    logging.error(f"Error connecting to the database: {e}")
    raise

  if columns_to_ignore:
    df_clean = df.drop(columns=columns_to_ignore, errors='ignore')
  else:
    df_clean = df

  for col in df_clean.columns:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='ignore')

  # Prevent Timestamp types from crashing DictVectorizer
  for col in df_clean.columns:
    if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
      df_clean[col] = df_clean[col].astype(str)

  data_dict = df_clean.to_dict(orient='records')

  #Instantiating the vectorizer model
  translator = DictVectorizer(sparse=False)
  X_practice = translator.fit_transform(data_dict)

  # Scale features — IsolationForest is sensitive to feature scale.
  # Numeric columns (V1, V2, Amount) may have vastly different ranges,
  # and without scaling, large-range features dominate the anomaly score.
  scaler = StandardScaler()
  X_scaled = scaler.fit_transform(X_practice)

  #Instantianting the ML model
  i_forest = IsolationForest(contamination=contamination,random_state=42)
  i_forest.fit(X_scaled)

  models_dir = os.path.join(os.getcwd(), 'models')
  model_metadata = save_versioned_models(
      target_table=target_table,
      models_dir=models_dir,
      translator=translator,
      isolation_forest=i_forest,
      scaler=scaler,
  )

  metrics = {
    "samples": int(len(df_clean)),
    "feature_count": int(df_clean.shape[1]),
    "rf_model_trained": False,
    "labeled_data": 0,
    "fraud_count": 0,
  }

  engine_internal = get_db_engine_internal()
  insert_model_version_record(
    engine_internal,
    target_table,
    model_metadata["version"],
    model_metadata["paths"],
    metrics=metrics,
    is_active=False,
  )