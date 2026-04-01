import joblib
from typing import Any,Dict,List
from sklearn.feature_extraction import DictVectorizer

class DynamicPreprocessor:

  def __init__(self, table_name:str,columns_to_ignore: List[str]):

    self.translator: DictVectorizer = joblib.load(f"models/{table_name}_translator.pkl")

    self.columns_to_ignore = columns_to_ignore or []

  def transform_json_to_features(self,kafka_json: Dict[str, Any]):
    """
    Recieves the raw json from kafka and returns the processed matrix to the models
    """

    #Assure that the models wont use useless columns like ids or raw dates
    clean_json = {k: v for k,v in kafka_json.items() if k not in self.columns_to_ignore}

    features = self.translator.transform([clean_json])

    return features