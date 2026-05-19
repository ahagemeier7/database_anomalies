import os
import logging
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

load_dotenv()

_db_engine: Engine = None


def _create_db_engine(user: str, password: str, db_name: str, server: str) -> Engine:
    return create_engine(f"postgresql://{user}:{password}@{server}/{db_name}")


def get_db_engine() -> Engine:

  global _db_engine

  if _db_engine:
    return _db_engine
  
  db_user = os.getenv("POSTGRES_USER_INTERNAL") or os.getenv("POSTGRES_USER")
  db_password = os.getenv("POSTGRES_PASSWORD_INTERNAL") or os.getenv("POSTGRES_PASSWORD")
  db_name = os.getenv("POSTGRES_DB_INTERNAL") or os.getenv("POSTGRES_DB")
  db_server = os.getenv("POSTGRES_SERVER_INTERNAL") or os.getenv("POSTGRES_SERVER")

  required_vars = {
    "POSTGRES_USER_INTERNAL/POSTGRES_USER": db_user,
    "POSTGRES_PASSWORD_INTERNAL/POSTGRES_PASSWORD": db_password,
    "POSTGRES_DB_INTERNAL/POSTGRES_DB": db_name,
    "POSTGRES_SERVER_INTERNAL/POSTGRES_SERVER": db_server,
  }

  missing_vars = [key for key, value in required_vars.items() if not value]
  if missing_vars:
    logging.error(f"Couldn't connect to the database, missing variables: {', '.join(missing_vars)}")
    sys.exit(1)

  try:
    _db_engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_server}/{db_name}")
    return _db_engine
  except Exception as e:
    logging.error(f"Error creating database engine: {e}")
    sys.exit(1)