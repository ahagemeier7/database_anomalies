// src/services/fraudService.ts
import api from './api';
import type { Pipeline, Anomaly } from '../types/types';

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

  // 3. Buscar Anomalias (Opcional: filtrar por tabela)
  getAnomalies: async (status: string = 'pending_revision'): Promise<Anomaly[]> => {
    // Aqui a gente já poderia passar o target_table pro backend no futuro
    const response = await api.get(`/anomalies?status=${status}`);
    return response.data.anomalies;
  },

  // 4. Atualizar Status (Julgamento do Humano)
  updateAnomalyStatus: async (alertId: string, status: 'confirmed_fraud' | 'false_positive'): Promise<{ message: string }> => {
    const response = await api.put(`/anomalies/${alertId}/status`, { status });
    return response.data;
  }
};