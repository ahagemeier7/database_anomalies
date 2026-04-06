import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

load_dotenv()

def get_db_engine() -> Engine:
  db_user = os.getenv("POSTGRES_USER")
  db_password = os.getenv("POSTGRES_PASSWORD")
  db_name = os.getenv("POSTGRES_DB")
  db_server = os.getenv("POSTGRES_SERVER")

  try:
    engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_server}/{db_name}")
    return engine
  except Exception as e:
    print(f"Error creating database engine: {e}")
    raise