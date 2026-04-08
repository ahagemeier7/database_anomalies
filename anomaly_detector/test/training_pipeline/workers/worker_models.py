import os
import logging
import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest
from anomaly_detector.test.training_pipeline.db.db import get_db_engine
import pandas as pd


def train_models(target_table: str,columns_to_ignore:list = None) -> None:

  #fetching DB data
  try:
    engine = get_db_engine()

    df = pd.read_sql(f"SELECT * FROM {target_table}", engine)
  except Exception as e:
    logging.error(f"Error connecting to the database: {e}")
    raise

  df_clean = df.drop(columns=columns_to_ignore, errors='ignore')

  data_dict = df_clean.to_dict(orient='records')

  #Instantiating the vectorizer model
  translator = DictVectorizer(sparse=False)
  X_practice = translator.fit_transform(data_dict)

  #Instantianting the ML model
  i_forest = IsolationForest(contamination=0.01,random_state=42)
  i_forest.fit(X_practice)

  base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  models_dir = os.path.join(base_dir, 'models')
    
  os.makedirs(models_dir, exist_ok=True)

  translator_path = os.path.join(models_dir, f'{target_table}_translator.pkl')
  model_path = os.path.join(models_dir, f'{target_table}_model.pkl')

  joblib.dump(translator, translator_path)
  joblib.dump(i_forest, model_path)