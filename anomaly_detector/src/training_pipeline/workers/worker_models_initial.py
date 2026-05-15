import os
import logging
import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest
from src.training_pipeline.db.db_source import get_db_engine
import pandas as pd


def train_models(target_table: str,columns_to_ignore:list = None) -> None:

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

  df_clean = df_clean.apply(pd.to_numeric, errors='ignore')

  # Prevent Timestamp types from crashing DictVectorizer
  for col in df_clean.columns:
    if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
      df_clean[col] = df_clean[col].astype(str)

  data_dict = df_clean.to_dict(orient='records')

  #Instantiating the vectorizer model
  translator = DictVectorizer(sparse=False)
  X_practice = translator.fit_transform(data_dict)

  #Instantianting the ML model
  i_forest = IsolationForest(contamination=0.1,random_state=42)
  i_forest.fit(X_practice)

  models_dir = os.path.join(os.getcwd(), 'models')
    
  os.makedirs(models_dir, exist_ok=True)

  translator_path = os.path.join(models_dir, f'{target_table}_translator.pkl')
  model_path = os.path.join(models_dir, f'{target_table}_if_model.pkl')

  joblib.dump(translator, translator_path)
  joblib.dump(i_forest, model_path)