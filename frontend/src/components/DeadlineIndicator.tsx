import { differenceInDays, format, isPast } from 'date-fns';
import { ClockIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/solid';

interface DeadlineIndicatorProps {
  deadline: string;
  className?: string;
  compact?: boolean;
}

export default function DeadlineIndicator({
  deadline,
  className = '',
  compact = false,
}: DeadlineIndicatorProps) {
  const deadlineDate = new Date(deadline);
  const daysRemaining = differenceInDays(deadlineDate, new Date());
  const isOverdue = isPast(deadlineDate);

  let colorClass = 'text-success-500';
  let bgClass = 'bg-success-500/20 border-success-500/30';
  let Icon = CheckCircleIcon;
  let label = `${daysRemaining}d`;

  if (isOverdue) {
    colorClass = 'text-danger-400';
    bgClass = 'bg-danger-500/20 border-danger-500/30';
    Icon = ExclamationTriangleIcon;
    label = `${Math.abs(daysRemaining)}d overdue`;
  } else if (daysRemaining <= 3) {
    colorClass = 'text-danger-400';
    bgClass = 'bg-danger-500/20 border-danger-500/30';
    Icon = ExclamationTriangleIcon;
    label = `${daysRemaining}d`;
  } else if (daysRemaining <= 7) {
    colorClass = 'text-warning-400';
    bgClass = 'bg-warning-500/20 border-warning-500/30';
    Icon = ClockIcon;
    label = `${daysRemaining}d`;
  } else if (daysRemaining <= 14) {
    colorClass = 'text-warning-400';
    bgClass = 'bg-warning-500/20 border-warning-500/30';
    Icon = ClockIcon;
    label = `${daysRemaining}d`;
  } else {
    colorClass = 'text-success-500';
    bgClass = 'bg-success-500/20 border-success-500/30';
    Icon = ClockIcon;
    label = `${daysRemaining}d`;
  }

  if (compact) {
    return (
      <div className={`flex items-center gap-1.5 ${className}`}>
        <Icon className={`h-4 w-4 ${colorClass}`} />
        <span className={`text-sm font-medium ${colorClass}`}>{label}</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border ${bgClass} ${className}`}>
      <Icon className={`h-4 w-4 ${colorClass}`} />
      <div className="text-xs">
        <div className={`font-semibold ${colorClass}`}>
          {isOverdue ? 'Overdue' : `${daysRemaining} days left`}
        </div>
        <div className="text-navy-400">{format(deadlineDate, 'MMM d, yyyy')}</div>
      </div>
    </div>
  );
}
