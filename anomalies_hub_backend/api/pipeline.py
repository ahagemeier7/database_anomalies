import sys
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.engine import Engine

from db.db import get_db_engine
from schemas.schemas import (
    RetrainResponse,
    PipelineListResponse,
    PipelineConfigResponse,
    InferenceModeUpdatePayload,
    InferenceModeUpdateResponse,
    ModelVersionListResponse,
    ModelVersionItem,
    ActivationResponse,
)
from crud import pipeline

sys.path.append('/app')
from src.training_pipeline.workers.worker_models_retraining import retrain_hybrid_models

router = APIRouter()

def get_db():
  return get_db_engine()

@router.get(
    "/pipelines",
    tags=["Config"],
    response_model=PipelineListResponse,
    summary="Listar pipelines de ML",
    description="Retorna todas as pipelines de detecção configuradas, "
                "incluindo a contagem de anomalias pendentes por tabela.",
)
def fetch_pipelines(db: Engine = Depends(get_db)):
  try:
    return {"pipelines": pipeline.get_all_pipelines(db)}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/pipelines/{target_table}",
    tags=["Config"],
    response_model=PipelineConfigResponse,
    summary="Obter configuração da pipeline",
    description="Retorna a configuração atual da pipeline, incluindo o modo de inferência selecionado.",
)
def get_pipeline_configuration(target_table: str, db: Engine = Depends(get_db)):
  try:
    config = pipeline.get_pipeline_config(db, target_table)
    if not config:
      raise HTTPException(status_code=404, detail="Pipeline not found.")
    return {
      "target_table": target_table,
      "inference_mode": config.get("inference_mode") or "hybrid",
    }
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pipelines/{target_table}/inference-mode",
    tags=["Config"],
    response_model=InferenceModeUpdateResponse,
    summary="Atualizar modo de inferência",
    description="Persiste o modo de inferência selecionado para a pipeline alvo.",
)
def update_inference_mode(target_table: str, payload: InferenceModeUpdatePayload, db: Engine = Depends(get_db)):
  try:
    pipeline.update_pipeline_inference_mode(db, target_table, payload.inference_mode)
    return {
      "message": f"Inference mode updated for {target_table}.",
      "inference_mode": payload.inference_mode,
    }
  except ValueError as ve:
    raise HTTPException(status_code=400, detail=str(ve))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pipelines/{target_table}/retrain",
    tags=["Machine Learning"],
    response_model=RetrainResponse,
    summary="Disparar retreinamento de modelo",
    description="Inicia o retreinamento assíncrono dos modelos híbridos "
                "(Isolation Forest + Random Forest) para a tabela alvo informada. "
                "A tarefa é executada em background.",
)
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


@router.get(
    "/pipelines/{target_table}/versions",
    tags=["Machine Learning"],
    response_model=ModelVersionListResponse,
    summary="Listar versões de modelo",
    description="Retorna todas as versões de modelo disponíveis para a pipeline alvo.",
)
def list_model_versions(target_table: str, db: Engine = Depends(get_db)):
  try:
    return {"versions": pipeline.get_model_versions(db, target_table)}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pipelines/{target_table}/versions/active",
    tags=["Machine Learning"],
    response_model=ModelVersionItem,
    summary="Versão ativa do modelo",
    description="Retorna a versão atualmente ativa do modelo para a pipeline alvo.",
)
def get_active_model_version(target_table: str, db: Engine = Depends(get_db)):
  try:
    active = pipeline.get_active_model_version(db, target_table)
    if not active:
      raise HTTPException(status_code=404, detail="Active model version not found.")
    return active
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pipelines/{target_table}/versions/{version}/activate",
    tags=["Machine Learning"],
    response_model=ActivationResponse,
    summary="Ativar versão de modelo",
    description="Ativa a versão de modelo especificada e marca-a como ativa na pipeline.",
)
def activate_model_version(target_table: str, version: str, db: Engine = Depends(get_db)):
  try:
    pipeline.activate_model_version(db, target_table, version)
    return {
      "message": f"Model version {version} activated for {target_table}.",
      "active_version": version,
    }
  except ValueError as ve:
    raise HTTPException(status_code=404, detail=str(ve))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
