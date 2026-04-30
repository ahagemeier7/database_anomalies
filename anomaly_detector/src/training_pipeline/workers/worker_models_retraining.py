import os
import json
import logging
import joblib
import pandas as pd
from dotenv import load_dotenv
from anomaly_detector.src.training_pipeline.db.db_internal import get_db_engine as get_db_engine_iternal
from anomaly_detector.src.training_pipeline.db.db_source import get_db_engine as get_db_engine_source
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest, RandomForestClassifier

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retrain_models(target_table: str, columns_to_ignore: list = None) -> None:

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

    df_features = df_features.apply(pd.to_numeric, errors='ignore')

    # Convert dates to string to work with dict vectorizer
    for col in df_features.columns:
        if pd.api.types.is_datetime64_any_dtype(df_features[col]):
            df_features[col] = df_features[col].astype(str)

    data_dict = df_features.to_dict(orient='records')

    translator = DictVectorizer(sparse=False)

    X = translator.fit_transform(data_dict)
    y = df_source['is_fraud']

    i_forest = IsolationForest(contamination=0.1,random_state=42)
    i_forest.fit(X)

    rf_trained = False

    if 1 in y.values:
      r_forest = RandomForestClassifier(n_estimators=100,random_state=42,n_jobs=-1)
      r_forest.fit(X,y)

      rf_trained = True
    else:
      logging.warning('No classified fraud found, skipping random forest')

    models_dir = os.path.join(os.getcwd(), 'models')
    os.makedirs(models_dir, exist_ok=True)

    translator_path = os.path.join(models_dir, f'{target_table}_translator.pkl')
    if_model_path = os.path.join(models_dir, f'{target_table}_if_model.pkl')
    rf_model_path = os.path.join(models_dir, f'{target_table}_rf_model.pkl')

    joblib.dump(translator, translator_path)
    joblib.dump(i_forest, if_model_path)
        
    if rf_trained:
      joblib.dump(r_forest, rf_model_path)
    else:
      logging.info(f"Isolation Forest saved in {models_dir}")

  except Exception as e:
    logging.error(f"Critical error during model retrain {e}")
    raise 