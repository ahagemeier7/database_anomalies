from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Request payloads ──────────────────────────────────────────────

class StatusUpdatePayload(BaseModel):
    status: str = Field(
        ...,
        description="Novo status do alerta ('confirmed_fraud', 'false_positive' ou 'pending_revision')",
    )


# ── Anomalies ─────────────────────────────────────────────────────

class AnomalyItem(BaseModel):
    alert_id: str
    timestamp_detection: datetime
    origin_table: str
    ml_model: str
    status: str
    raw_event: dict[str, Any] | None = None


class AnomalyListResponse(BaseModel):
    anomalies: list[AnomalyItem]
    total: int


class StatusUpdateResponse(BaseModel):
    message: str


# ── Dashboard stats ───────────────────────────────────────────────

class ModelMetrics(BaseModel):
    precision: float


class ChartDataPoint(BaseModel):
    date: date
    frauds: int | None = 0
    false_positives: int | None = 0


class DashboardStats(BaseModel):
    total_alerts: int
    pending_reviews: int
    confirmed_frauds: int
    false_positives: int
    model_metrics: ModelMetrics
    history_chart: list[ChartDataPoint]


# ── Per-table stats ───────────────────────────────────────────────

class TableStatsItem(BaseModel):
    origin_table: str
    total_alerts: int
    pending_reviews: int
    confirmed_frauds: int
    false_positives: int
    precision: float


# ── Pipelines ─────────────────────────────────────────────────────

class PipelineItem(BaseModel):
    target_table: str
    pipeline_name: str | None = None
    columns_to_ignore: str | None = None
    date_columns: str | None = None
    inference_mode: str | None = None
    status: str | None = None
    last_startup: datetime | None = None
    pending_count: int = 0


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineItem]


class PipelineConfigResponse(BaseModel):
    target_table: str
    inference_mode: str | None = None


class InferenceModeUpdatePayload(BaseModel):
    inference_mode: str = Field(..., description="Modo de inferência desejado: if, rf ou hybrid")


class InferenceModeUpdateResponse(BaseModel):
    message: str
    inference_mode: str


class ModelVersionItem(BaseModel):
    target_table: str
    version: str
    translator_path: str
    if_model_path: str
    scaler_path: str
    rf_model_path: str | None = None
    metrics: dict[str, Any] | None = None
    is_active: bool = False
    created_at: datetime


class ModelVersionListResponse(BaseModel):
    versions: list[ModelVersionItem]


class ActivationResponse(BaseModel):
    message: str
    active_version: str


class RetrainResponse(BaseModel):
    message: str
