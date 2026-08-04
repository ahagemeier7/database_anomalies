import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Layers, CheckCircle, ArrowRightCircle, Settings2 } from 'lucide-react';
import { fraudService } from '../services/services';
import type { ModelVersion } from '../types/types';
import { Button, Card, PageHeader, SkeletonCard, ErrorBanner, EmptyState, useToast } from '../components/ui';

export default function ModelVersionsPage() {
  const { tableName } = useParams();
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [inferenceMode, setInferenceMode] = useState<'if' | 'rf' | 'hybrid'>('hybrid');
  const [modeSaving, setModeSaving] = useState(false);
  const [modeError, setModeError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchVersions = () => {
    if (!tableName) return;
    setLoading(true);
    setError(null);

    fraudService.getModelVersions(tableName)
      .then(data => setVersions(data))
      .catch(() => setError('Failed to load model versions. Is the backend running?'))
      .finally(() => setLoading(false));
  };

  const fetchPipelineConfig = () => {
    if (!tableName) return;

    fraudService.getPipelineConfig(tableName)
      .then(data => {
        setInferenceMode((data.inference_mode as 'if' | 'rf' | 'hybrid') || 'hybrid');
        setModeError(null);
      })
      .catch(() => setModeError('Could not load the current inference mode.'));
  };

  useEffect(() => {
    fetchVersions();
    fetchPipelineConfig();
  }, [tableName]);

  const handleActivate = async (version: string) => {
    if (!tableName) return;
    setActivating(version);
    try {
      const response = await fraudService.activateModelVersion(tableName, version);
      toast(`Activated ${response.active_version} for ${tableName}`, 'success');
      fetchVersions();
    } catch {
      toast('Failed to activate selected version.', 'error');
    } finally {
      setActivating(null);
    }
  };

  const handleInferenceModeChange = async (mode: 'if' | 'rf' | 'hybrid') => {
    if (!tableName) return;
    setModeSaving(true);
    setModeError(null);
    try {
      await fraudService.updatePipelineInferenceMode(tableName, mode);
      setInferenceMode(mode);
      toast(`Inference mode set to ${mode} for ${tableName}`, 'success');
    } catch {
      setModeError('Failed to update inference mode. Please try again.');
      toast('Failed to update inference mode.', 'error');
    } finally {
      setModeSaving(false);
    }
  };

  return (
    <div>
      <PageHeader
        title={`Model Versions${tableName ? ` — ${tableName}` : ''}`}
        subtitle={tableName ? `Manage model versions for ${tableName}` : 'Select a pipeline to view versions'}
      />

      {loading && (
        <div className="grid grid-cols-1 gap-4">
          {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={fetchVersions} />}

      {!loading && !error && tableName && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600">
                <Settings2 className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Inference mode</p>
                <p className="text-sm text-slate-500">Choose which model strategy the worker should use for this pipeline.</p>
              </div>
            </div>
            <div className="flex flex-col gap-2 sm:items-end">
              <select
                value={inferenceMode}
                onChange={(event) => handleInferenceModeChange(event.target.value as 'if' | 'rf' | 'hybrid')}
                disabled={modeSaving}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-slate-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
              >
                <option value="if">Isolation Forest</option>
                <option value="rf">Random Forest</option>
                <option value="hybrid">Hybrid</option>
              </select>
              {modeSaving && <p className="text-xs text-slate-500">Saving...</p>}
              {modeError && <p className="text-xs text-rose-600">{modeError}</p>}
            </div>
          </div>
        </div>
      )}

      {!loading && !error && versions.length === 0 && (
        <EmptyState
          icon={Layers}
          title="No model versions"
          description={tableName ? `No versions were found for ${tableName}.` : 'Select a pipeline to view saved model versions.'}
        />
      )}

      {!loading && !error && versions.length > 0 && (
        <div className="space-y-4">
          {versions.map(version => (
            <Card key={version.version} className="border-l-4 border-l-slate-300">
              <div className="flex items-center justify-between gap-4 mb-3">
                <div>
                  <p className="text-base font-semibold text-gray-900">{version.version}</p>
                  <p className="text-sm text-gray-500">Created at {new Date(version.created_at).toLocaleString()}</p>
                  {version.is_active && (
                    <p className="mt-1 text-sm text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle className="h-4 w-4" /> Active version
                    </p>
                  )}
                </div>
                <Button
                  variant={version.is_active ? 'ghost' : 'primary'}
                  size="sm"
                  icon={<ArrowRightCircle className="h-4 w-4" />}
                  loading={activating === version.version}
                  disabled={version.is_active}
                  onClick={() => handleActivate(version.version)}
                >
                  {version.is_active ? 'Active' : 'Activate'}
                </Button>
              </div>

              <div className="grid gap-2 sm:grid-cols-2 text-sm text-gray-600">
                <div>
                  <p className="font-semibold">Translator</p>
                  <p>{version.translator_path}</p>
                </div>
                <div>
                  <p className="font-semibold">Isolation Forest</p>
                  <p>{version.if_model_path}</p>
                </div>
                <div>
                  <p className="font-semibold">Scaler</p>
                  <p>{version.scaler_path}</p>
                </div>
                {version.rf_model_path && (
                  <div>
                    <p className="font-semibold">Random Forest</p>
                    <p>{version.rf_model_path}</p>
                  </div>
                )}
              </div>

              {version.metrics && (
                <div className="mt-4 bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
                  <p className="font-semibold mb-2">Metrics</p>
                  <pre className="whitespace-pre-wrap break-words text-xs">{JSON.stringify(version.metrics, null, 2)}</pre>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
