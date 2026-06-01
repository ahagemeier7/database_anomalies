import os
import joblib
from typing import Any,Dict,List
from sklearn.feature_extraction import DictVectorizer

class DynamicPreprocessor:

  def __init__(self, table_name:str,columns_to_ignore: List[str]):

    self.translator: DictVectorizer = joblib.load(f"models/{table_name}_translator.pkl")

    # Load scaler if available — models trained after the StandardScaler
    # introduction will have it; legacy models work without it.
    scaler_path = f"models/{table_name}_scaler.pkl"
    if os.path.exists(scaler_path):
      self.scaler = joblib.load(scaler_path)
    else:
      self.scaler = None

    self.columns_to_ignore = columns_to_ignore or []

  def transform_json_to_features(self,kafka_json: Dict[str, Any]):
    """
    Recieves the raw json from kafka and returns the processed matrix to the models
    """

    #Assuring that the models wont use useless columns like ids or raw dates as features
    clean_json = {k: v for k,v in kafka_json.items() if k not in self.columns_to_ignore}

    for k, v in clean_json.items():
        if isinstance(v, str):
            try:
                clean_json[k] = float(v)
            except ValueError:
                pass

    features = self.translator.transform([clean_json])

    # Apply the same scaling used during training so features
    # are on the same scale the model expects.
    if self.scaler is not None:
      features = self.scaler.transform(features)

    return features