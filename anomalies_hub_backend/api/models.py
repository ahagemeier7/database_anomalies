import sys
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

sys.path.append('/app')
from src.training_pipeline.workers import model_versioning as mv

from db.db import get_db_engine
from schemas.schemas import ModelVersionItem

router = APIRouter()

def get_db():
  return get_db_engine()


@router.post('/models/register', tags=['Models'], summary='Register model version')
def register_model(payload: dict, db: Engine = Depends(get_db)):
  try:
    # Expecting payload keys: target_table, version, paths, metrics, is_active
    target_table = payload.get('target_table')
    version = payload.get('version')
    paths = payload.get('paths')
    metrics = payload.get('metrics')
    is_active = bool(payload.get('is_active', False))

    if not target_table or not version or not paths:
      raise HTTPException(status_code=400, detail='target_table, version and paths are required')

    mv.insert_model_version_record(db, target_table, version, paths, metrics=metrics, is_active=is_active)

    return {'message': 'registered'}
  except HTTPException:
    raise
  except Exception as e:
    logging.error('Failed to register model: %s', e)
    raise HTTPException(status_code=500, detail=str(e))


@router.get('/models/status', tags=['Models'], summary='Get active model status')
def get_models_status(target_table: str | None = None, db: Engine = Depends(get_db)):
  try:
    if target_table:
      active = mv.get_active_model_version(db, target_table)
      if not active:
        raise HTTPException(status_code=404, detail='Active model version not found')
      return active
    else:
      # Not implemented: list all active versions; return empty list
      return []
  except HTTPException:
    raise
  except Exception as e:
    logging.error('Failed to get model status: %s', e)
    raise HTTPException(status_code=500, detail=str(e))
