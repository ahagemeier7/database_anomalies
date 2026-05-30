export interface Pipeline {
  target_table: string;
  pipeline_name: string;
  status: string;
  last_startup: string;
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