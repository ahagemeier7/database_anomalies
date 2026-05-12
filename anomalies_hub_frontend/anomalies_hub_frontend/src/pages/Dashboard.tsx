// src/pages/WorkersPage.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { Pipeline } from '../types/types';

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Pipeline[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/pipelines').then(response => {
      setWorkers(response.data.pipelines);
    }).catch(error => console.error("Erro ao buscar workers:", error));
  },[]);

  const handleRetrain = async (tableName: string) => {
    try {
      alert(`Solicitando retreino para ${tableName}... Acompanhe o terminal do Backend!`);
      await api.post(`/pipelines/${tableName}/retrain`);
    } catch (error) {
      alert("Erro ao solicitar retreino.");
    }
  };

  return (
    <div>
      <h2>Workers Ativos</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
        
        {workers.map(worker => (
          <div key={worker.target_table} style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '8px' }}>
            <h3>{worker.pipeline_name}</h3>
            <p><strong>Tabela:</strong> {worker.target_table}</p>
            <p><strong>Status:</strong> {worker.status}</p>
            
            <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
              <button onClick={() => navigate(`/revisions/${worker.target_table}`)}>
                Ver Revisões
              </button>
              <button onClick={() => handleRetrain(worker.target_table)} style={{ background: '#27ae60', color: 'white' }}>
                Retreinar IA
              </button>
            </div>
          </div>
        ))}

      </div>
    </div>
  );
}