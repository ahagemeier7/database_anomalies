from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine

from db.db import get_db_engine
from schemas.schemas import (
    StatusUpdatePayload,
    AnomalyListResponse,
    StatusUpdateResponse,
    DashboardStats,
    TableStatsItem,
)
from crud import anomalies

router = APIRouter()

def get_db():
  return get_db_engine()

@router.get(
    "/anomalies",
    tags=["Anomalies"],
    response_model=AnomalyListResponse,
    summary="Listar anomalias",
    description="Retorna anomalias paginadas filtradas por status. "
                "Suporta filtro opcional por tabela de origem (`origin_table`).",
)
def fetch_anomalies(
  status: str = "pending_revision",
  limit: int = 25,
  offset: int = 0,
  origin_table: str | None = None,
  db: Engine = Depends(get_db)
):
  try:
    items = anomalies.get_anomalies_by_status(db, status, limit=limit, offset=offset, origin_table=origin_table)
    total = anomalies.count_anomalies_by_status(db, status, origin_table=origin_table)
    return {"anomalies": items, "total": total}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/anomalies/{alert_id}/status",
    tags=["Anomalies"],
    response_model=StatusUpdateResponse,
    summary="Atualizar status de um alerta",
    description="Atualiza o status de uma anomalia para `confirmed_fraud`, "
                "`false_positive` ou `pending_revision`.",
)
def update_anomaly(alert_id: str, payload: StatusUpdatePayload, db: Engine = Depends(get_db)):
  valid_statuses =["confirmed_fraud", "false_positive", "pending_revision"]
  if payload.status not in valid_statuses:
    raise HTTPException(status_code=400, detail=f"Status deve ser: {valid_statuses}")

  try:
    anomalies.update_status(db, alert_id, payload.status)
    return {"message": f"Alert {alert_id} updated to '{payload.status}'!"}
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/anomalies/stats",
    tags=["Anomalies"],
    response_model=DashboardStats,
    summary="Estatísticas do dashboard",
    description="Retorna contagens agregadas de anomalias, métricas de precisão do modelo "
                "e histórico dos últimos 7 dias para o gráfico do dashboard.",
)
def fetch_dashboard_stats(db: Engine = Depends(get_db)):
  try:
    return anomalies.get_dashboard_stats(db)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/anomalies/stats/by-table",
    tags=["Anomalies"],
    response_model=list[TableStatsItem],
    summary="Estatísticas por tabela",
    description="Retorna as estatísticas de anomalias agrupadas por `origin_table`, "
                "incluindo precisão calculada por tabela.",
)
def fetch_stats_by_table(db: Engine = Depends(get_db)):
  try:
    return anomalies.get_stats_by_table(db)
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
