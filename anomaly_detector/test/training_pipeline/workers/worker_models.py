import logging
import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest
from anomaly_detector.test.training_pipeline.db.db import get_db_engine
import pandas as pd


def train_models(target_table: str) -> None:

  #fetching DB data
  try:
    engine = get_db_engine()

    df = pd.read_sql(f"SELECT * FROM {target_table}", engine)
  except Exception as e:
    logging.error(f"Error connecting to the database: {e}")
    raise

  #Instantiating the vectorizer model
  translator = DictVectorizer(sparse=False)
  X_practice = translator.fit_transform(df)

  #Instantianting the ML model
  i_forest = IsolationForest(contamination=0.01,random_state=42)
  i_forest.fit(X_practice)

  #Saving both models
  joblib.dump(translator,f'models/{target_table}_translator.pkl')
  joblib.dump(translator,f'models/{target_table}_model.pkl')