import {
  LockClosedIcon,
  ShieldCheckIcon,
  GlobeAltIcon,
  DocumentIcon,
  EyeSlashIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface ClassificationBadgeProps {
  classification: 'responsive' | 'non_responsive' | 'partially_responsive' | 'exempt' | 'unclassified' | 'public' | 'confidential' | 'restricted';
  size?: 'sm' | 'md' | 'lg';
  showConfidence?: boolean;
  confidence?: number;
}

const classificationConfig = {
  responsive: {
    icon: CheckCircleIcon,
    label: 'Responsive',
    color: 'bg-success-500/20 text-success-500 border-success-500/30',
  },
  non_responsive: {
    icon: XCircleIcon,
    label: 'Non-Responsive',
    color: 'bg-navy-500/20 text-navy-400 border-navy-500/30',
  },
  partially_responsive: {
    icon: ShieldCheckIcon,
    label: 'Partial',
    color: 'bg-warning-500/20 text-warning-400 border-warning-500/30',
  },
  exempt: {
    icon: EyeSlashIcon,
    label: 'Exempt',
    color: 'bg-danger-500/20 text-danger-400 border-danger-500/30',
  },
  public: {
    icon: GlobeAltIcon,
    label: 'Public',
    color: 'bg-success-500/20 text-success-500 border-success-500/30',
  },
  unclassified: {
    icon: DocumentIcon,
    label: 'Pending',
    color: 'bg-navy-500/20 text-navy-400 border-navy-500/30',
  },
  confidential: {
    icon: ShieldCheckIcon,
    label: 'Confidential',
    color: 'bg-warning-500/20 text-warning-400 border-warning-500/30',
  },
  restricted: {
    icon: LockClosedIcon,
    label: 'Restricted',
    color: 'bg-danger-500/20 text-danger-400 border-danger-500/30',
  },
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

const iconSizes = {
  sm: 'h-3 w-3',
  md: 'h-3.5 w-3.5',
  lg: 'h-4 w-4',
};

export default function ClassificationBadge({
  classification,
  size = 'md',
  showConfidence = false,
  confidence,
}: ClassificationBadgeProps) {
  const config = classificationConfig[classification] || classificationConfig.unclassified;
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1.5 rounded-lg font-medium border ${config.color} ${sizeClasses[size]}`}
      >
        <Icon className={iconSizes[size]} />
        {config.label}
      </span>
      {showConfidence && confidence !== undefined && (
        <span className="text-xs text-navy-500">{Math.round(confidence * 100)}%</span>
      )}
    </div>
  );
}
