import {
  Play, Pause, AlertTriangle, Clock, AlertOctagon,
  CheckCircle, HelpCircle, Activity,
} from 'lucide-react';

interface StatusBadgeProps {
  status: string;
}

const statusMap: Record<string, { icon: typeof Activity; color: string; label: string }> = {
  running: { icon: Play, color: 'bg-emerald-100 text-emerald-800', label: 'Running' },
  active: { icon: Play, color: 'bg-emerald-100 text-emerald-800', label: 'Active' },
  idle: { icon: Pause, color: 'bg-amber-100 text-amber-800', label: 'Idle' },
  stopped: { icon: Pause, color: 'bg-amber-100 text-amber-800', label: 'Stopped' },
  error: { icon: AlertTriangle, color: 'bg-red-100 text-red-800', label: 'Error' },
  pending_revision: { icon: Clock, color: 'bg-orange-100 text-orange-800', label: 'Pending' },
  confirmed_fraud: { icon: AlertOctagon, color: 'bg-red-100 text-red-800', label: 'Fraud' },
  false_positive: { icon: CheckCircle, color: 'bg-blue-100 text-blue-800', label: 'FP' },
};

const fallback = { icon: HelpCircle, color: 'bg-gray-100 text-gray-600', label: 'Unknown' };

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusMap[status] ?? { ...fallback, label: status };
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  );
}
