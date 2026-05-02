import sys
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.engine import Engine

from db.db import get_db_engine
from schemas.schemas import RetrainResponse
from crud import pipeline

#Adding the /app sufix so that python finds the shared volume
sys.path.append('/app')
from training_pipeline.worker_models_retraining import retrain_hybrid_models

router = APIRouter()

def get_db():
  return get_db_engine()

@router.get("/pipelines", tags=["Config"])
def fetch_pipelines(db: Engine = Depends(get_db)):
  try:
    return {"pipelines": pipeline.get_all_pipelines(db)}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.post("/pipelines/{target_table}/retrain", tags=["Machine Learning"], response_model=RetrainResponse)
def trigger_retraining(target_table: str, bg_tasks: BackgroundTasks, db: Engine = Depends(get_db)):
  try:
    config = pipeline.get_pipeline_config(db, target_table)
    if not config:
      raise HTTPException(status_code=404, detail="Pipeline not found.")

    cols_to_ignore = config['columns_to_ignore'].split(',') if config['columns_to_ignore'] else[]
        
    bg_tasks.add_task(retrain_hybrid_models, target_table, cols_to_ignore)

    return {"message": f"Retrain started for the table: {target_table}."}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))