import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fraudService } from '../services/services';
import type { Anomaly } from '../types/types';

export default function RevisionsPage(){

const { tableName } = useParams();
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);

  useEffect(() => {
    fetchAnomalies();
  },[tableName]);

  const fetchAnomalies = () => {
    
    fraudService.getAnomalies('pending_revision')
      .then(data => {
        
        if (tableName) {
          data = data.filter((a: Anomaly) => a.origin_table === tableName);
        }
        setAnomalies(data);
      })
      .catch(error => console.error("Erro ao buscar anomalias:", error));
  };

  const handleAction = async (alertId: string, status: 'confirmed_fraud' | 'false_positive') => {
    try {
      await fraudService.updateAnomalyStatus(alertId, status);
    
      setAnomalies(prev => prev.filter(a => a.alert_id !== alertId));
    } catch (error) {
      alert("Erro ao atualizar status.");
    }
  };

  return (
    <div>
      <h2>Fila de Revisões {tableName ? `- ${tableName}` : '(Geral)'}</h2>
      {anomalies.length === 0 ? <p>Nenhuma anomalia pendente! 🎉</p> : null}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {anomalies.map(anomaly => (
          <div key={anomaly.alert_id} style={{ border: '1px solid #e74c3c', padding: '15px', borderRadius: '8px', background: '#fdfbfb' }}>
            <p><strong>Alerta:</strong> {anomaly.alert_id} | <strong>Modelo:</strong> {anomaly.ml_model}</p>
            <p><strong>Data:</strong> {new Date(anomaly.timestamp_detection).toLocaleString()}</p>
            
            <details style={{ margin: '10px 0', cursor: 'pointer' }}>
              <summary>Ver Dados da Transação</summary>
              <pre style={{ background: '#333', color: '#fff', padding: '10px', borderRadius: '5px' }}>
                {JSON.stringify(anomaly.raw_event, null, 2)}
              </pre>
            </details>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => handleAction(anomaly.alert_id, 'confirmed_fraud')} style={{ background: '#c0392b', color: 'white' }}>
                🔴 Confirmar Fraude
              </button>
              <button onClick={() => handleAction(anomaly.alert_id, 'false_positive')} style={{ background: '#2980b9', color: 'white' }}>
                🟢 Falso Positivo (Liberar)
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}