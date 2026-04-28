import os
import logging
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

load_dotenv()

_db_engine: Engine = None

def get_db_engine() -> Engine:

  global _db_engine

  if _db_engine:
    return _db_engine
  
  db_user = os.getenv("POSTGRES_USER_INTERNAL")
  db_password = os.getenv("POSTGRES_PASSWORD_INTERNAL")
  db_name = os.getenv("POSTGRES_DB_INTERNAL")
  db_server = os.getenv("POSTGRES_SERVER_INTERNAL")

  required_vars = {
    "POSTGRES_USER_INTERNAL": db_user, 
    "POSTGRES_PASSWORD_INTERNAL": db_password, 
    "POSTGRES_DB_INTERNAL": db_name, 
    "POSTGRES_SERVER_INTERNAL": db_server
  }

  missing_vars = [key for key, value in required_vars.items() if not value]
  if missing_vars:
    logging.error(f"Não foi possível conectar ao banco. Variáveis de ambiente faltando: {', '.join(missing_vars)}")
    sys.exit(1)

  try:
    _db_engine = create_engine(f"postgresql://{db_user}:{db_password}@{db_server}/{db_name}")
    return _db_engine
  except Exception as e:
    logging.error(f"Error creating database engine: {e}")
    sys.exit(1)