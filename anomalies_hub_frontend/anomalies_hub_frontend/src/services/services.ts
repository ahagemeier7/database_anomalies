// src/services/fraudService.ts
import api from './api';
import type { Pipeline, Anomaly, DashboardStats, TableStats } from '../types/types';

export const fraudService = {
  
  // 1. Buscar Pipelines (Workers)
  getPipelines: async (): Promise<Pipeline[]> => {
    const response = await api.get('/pipelines');
    return response.data.pipelines;
  },

  // 2. Retreinar a IA
  retrainPipeline: async (tableName: string): Promise<{ message: string }> => {
    const response = await api.post(`/pipelines/${tableName}/retrain`);
    return response.data;
  },

  // 3. Buscar Anomalias com paginação e filtro por tabela
  getAnomalies: async (
    status: string = 'pending_revision',
    limit: number = 25,
    offset: number = 0,
    originTable?: string,
  ): Promise<{ anomalies: Anomaly[]; total: number }> => {
    const params = new URLSearchParams({ status, limit: String(limit), offset: String(offset) });
    if (originTable) params.set('origin_table', originTable);
    const response = await api.get(`/anomalies?${params}`);
    return response.data;
  },

  // 4. Atualizar Status (Julgamento do Humano)
  updateAnomalyStatus: async (alertId: string, status: 'confirmed_fraud' | 'false_positive'): Promise<{ message: string }> => {
    const response = await api.put(`/anomalies/${alertId}/status`, { status });
    return response.data;
  },

  // 5. Estatísticas do dashboard (global)
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get('/anomalies/stats');
    return response.data;
  },

  // 6. Estatísticas por tabela
  getStatsByTable: async (): Promise<TableStats[]> => {
    const response = await api.get('/anomalies/stats/by-table');
    return response.data;
  }
};