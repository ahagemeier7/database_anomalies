export interface Pipeline {
  target_table: string;
  pipeline_name: string;
  status: string;
  last_startup: string;
  inference_mode?: string | null;
  // stats que vamos adicionar depois no backend:
  pending_count?: number; 
}

export interface Anomaly {
  alert_id: string;
  timestamp_detection: string;
  origin_table: string;
  ml_model: string;
  status: 'pending_revision' | 'confirmed_fraud' | 'false_positive';
  raw_event: Record<string, unknown>;
}

export interface DashboardStats {
  total_alerts: number;
  pending_reviews: number;
  confirmed_frauds: number;
  false_positives: number;
  model_metrics: { precision: number };
  history_chart: HistoryChartItem[];
}

export interface HistoryChartItem {
  date: string;
  frauds: number;
  false_positives: number;
}

export interface TableStats {
  origin_table: string;
  total_alerts: number;
  pending_reviews: number;
  confirmed_frauds: number;
  false_positives: number;
  precision: number;
}

export interface ModelVersion {
  target_table: string;
  version: string;
  translator_path: string;
  if_model_path: string;
  scaler_path: string;
  rf_model_path?: string;
  metrics?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
}