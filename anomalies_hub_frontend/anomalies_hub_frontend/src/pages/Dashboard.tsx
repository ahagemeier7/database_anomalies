import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Eye, RotateCw } from 'lucide-react';
import { fraudService } from '../services/services';
import type { Pipeline } from '../types/types';
import { Button, Card, StatusBadge, PageHeader, SkeletonCard, ErrorBanner, useToast } from '../components/ui';

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retraining, setRetraining] = useState<string | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const fetchPipelines = () => {
    setLoading(true);
    setError(null);
    fraudService.getPipelines()
      .then(data => setWorkers(data))
      .catch(() => setError('Failed to load pipelines. Is the backend running?'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchPipelines(); }, []);

  const handleRetrain = async (tableName: string) => {
    setRetraining(tableName);
    try {
      await fraudService.retrainPipeline(tableName);
      toast(`Retraining started for ${tableName}`, 'success');
    } catch {
      toast('Failed to start retraining.', 'error');
    } finally {
      setRetraining(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Active Workers"
        subtitle={`${workers.length} pipeline${workers.length !== 1 ? 's' : ''} registered`}
      />

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={fetchPipelines} />}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {workers.map(worker => (
            <Card key={worker.target_table}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-900">{worker.pipeline_name}</h3>
                <StatusBadge status={worker.status} />
              </div>

              <div className="space-y-2 text-sm text-gray-600 mb-4">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-gray-400" />
                  <span>{worker.target_table}</span>
                </div>
                {worker.last_startup && (
                  <p>Started: {new Date(worker.last_startup).toLocaleString()}</p>
                )}
                {worker.pending_count != null && worker.pending_count > 0 && (
                  <p className="text-amber-600 font-medium">{worker.pending_count} pending reviews</p>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<Eye className="h-4 w-4" />}
                  onClick={() => navigate(`/revisions/${worker.target_table}`)}
                >
                  Reviews
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<RotateCw className="h-4 w-4" />}
                  loading={retraining === worker.target_table}
                  onClick={() => handleRetrain(worker.target_table)}
                >
                  Retrain
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
