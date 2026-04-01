import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest
from db.db import get_db_engine
import pandas as pd

#fetching DB data
try:
  engine = get_db_engine()
  
  df = pd.read_sql("SELECT * FROM expenses", engine)
except Exception as e:
  print(f"Error connecting to the database: {e}")
  raise

#Instantiating the vectorizer model
translator = DictVectorizer(sparse=False)
X_practice = translator.fit_transform(df)

#Instantianting the ML model
i_forest = IsolationForest(contamination=0.01,random_state=42)
i_forest.fit(X_practice)

#Saving both models
joblib.dump(translator,'models/translator_expenses.pkl')
joblib.dump(translator,'models/iforest_expenses.pkl')