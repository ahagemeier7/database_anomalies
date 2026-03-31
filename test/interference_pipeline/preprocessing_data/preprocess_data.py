import joblib
from typing import Any,Dict

## This translator variable is going to be the translator DictVectorizer model that's already trained in our dataset with the other ML models
translator = 'x'

class DynamicPreprocessor:

  def __init__(self):
    self.translator= joblib.load(translator)

  def transform_json_to_features(self,kafka_json: Dict[str, Any]):
    """
    Recieves the raw json from kafka and returns the processed matrix to the models
    """
    #Assure that the models wont use useless columns like ids or raw dates
    columns_to_ignore = ['id','Column2']

    clean_json = {k: v for k,v in kafka_json.items() if k not in columns_to_ignore}

    features = self.translator.transform([clean_json])

    return features