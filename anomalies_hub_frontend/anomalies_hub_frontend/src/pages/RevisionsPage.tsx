import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Calendar, Hash, Brain, AlertOctagon, CheckCircle, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { fraudService } from '../services/services';
import type { Anomaly } from '../types/types';
import { Button, Card, PageHeader, SkeletonRow, ErrorBanner, EmptyState, useToast } from '../components/ui';

const PAGE_SIZE = 25;

export default function RevisionsPage() {
  const { tableName } = useParams();
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState<string | null>(null);
  const { toast } = useToast();

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const fetchAnomalies = () => {
    setLoading(true);
    setError(null);
    fraudService.getAnomalies('pending_revision', PAGE_SIZE, page * PAGE_SIZE, tableName)
      .then(data => {
        setAnomalies(data.anomalies);
        setTotal(data.total);
      })
      .catch(() => setError('Failed to load anomalies. Is the backend running?'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { setPage(0); }, [tableName]);
  useEffect(() => { fetchAnomalies(); }, [page, tableName]);

  const handleAction = async (alertId: string, status: 'confirmed_fraud' | 'false_positive') => {
    setActing(alertId);
    try {
      await fraudService.updateAnomalyStatus(alertId, status);
      if (anomalies.length === 1 && page > 0) {
        setPage(p => p - 1);
      } else {
        fetchAnomalies();
      }
      toast(status === 'confirmed_fraud' ? 'Fraud confirmed' : 'Marked as false positive', 'success');
    } catch {
      toast('Failed to update status.', 'error');
    } finally {
      setActing(null);
    }
  };

  return (
    <div>
      <PageHeader
        title={tableName ? `Reviews — ${tableName}` : 'All Pending Reviews'}
        subtitle={`${total} total / Page ${page + 1} of ${totalPages}`}
      />

      {loading && (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => <SkeletonRow key={i} />)}
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={fetchAnomalies} />}

      {!loading && !error && anomalies.length === 0 && (
        <EmptyState
          icon={Search}
          title="No pending anomalies"
          description={tableName ? `No alerts to review for ${tableName}.` : 'All caught up! No alerts need attention.'}
        />
      )}

      {!loading && !error && anomalies.length > 0 && (
        <>
          <div className="space-y-4">
            {anomalies.map(anomaly => (
              <Card key={anomaly.alert_id} className="border-l-4 border-l-red-400">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600 mb-3">
                  <span className="inline-flex items-center gap-1.5">
                    <Hash className="h-4 w-4 text-gray-400" />
                    {anomaly.alert_id}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Brain className="h-4 w-4 text-gray-400" />
                    {anomaly.ml_model}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    {new Date(anomaly.timestamp_detection).toLocaleString()}
                  </span>
                </div>

                <details className="mb-4 group">
                  <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700 select-none">
                    View transaction data
                  </summary>
                  <pre className="mt-2 bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto max-h-64">
                    {JSON.stringify(anomaly.raw_event, null, 2)}
                  </pre>
                </details>

                <div className="flex gap-2">
                  <Button
                    variant="danger"
                    size="sm"
                    icon={<AlertOctagon className="h-4 w-4" />}
                    loading={acting === anomaly.alert_id}
                    onClick={() => handleAction(anomaly.alert_id, 'confirmed_fraud')}
                  >
                    Confirm Fraud
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<CheckCircle className="h-4 w-4" />}
                    loading={acting === anomaly.alert_id}
                    onClick={() => handleAction(anomaly.alert_id, 'false_positive')}
                  >
                    False Positive
                  </Button>
                </div>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-6">
              <Button
                variant="ghost"
                size="sm"
                icon={<ChevronLeft className="h-4 w-4" />}
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-gray-500">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                icon={<ChevronRight className="h-4 w-4" />}
                disabled={page + 1 >= totalPages}
                onClick={() => setPage(p => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
