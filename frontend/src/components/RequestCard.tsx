import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { PIARequest } from '../services/requests';
import DeadlineIndicator from './DeadlineIndicator';
import {
  ClockIcon,
  UserIcon,
  DocumentTextIcon,
  FolderIcon,
} from '@heroicons/react/24/outline';

interface RequestCardProps {
  request: PIARequest;
}

const statusConfig: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  new: { label: 'New', color: 'text-tronas-400', bgColor: 'bg-tronas-500/20', borderColor: 'border-tronas-500/30' },
  in_progress: { label: 'In Progress', color: 'text-warning-400', bgColor: 'bg-warning-500/20', borderColor: 'border-warning-500/30' },
  pending_department_review: { label: 'Pending Review', color: 'text-purple-400', bgColor: 'bg-purple-500/20', borderColor: 'border-purple-500/30' },
  pending_ag_ruling: { label: 'AG Ruling', color: 'text-warning-400', bgColor: 'bg-warning-500/20', borderColor: 'border-warning-500/30' },
  released: { label: 'Released', color: 'text-success-500', bgColor: 'bg-success-500/20', borderColor: 'border-success-500/30' },
  closed_no_records: { label: 'Closed', color: 'text-navy-400', bgColor: 'bg-navy-500/20', borderColor: 'border-navy-500/30' },
  withdrawn: { label: 'Withdrawn', color: 'text-navy-400', bgColor: 'bg-navy-500/20', borderColor: 'border-navy-500/30' },
};

const priorityConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  low: { label: 'Low', color: 'text-navy-400', bgColor: 'bg-navy-500/20' },
  medium: { label: 'Medium', color: 'text-tronas-400', bgColor: 'bg-tronas-500/20' },
  high: { label: 'High', color: 'text-warning-400', bgColor: 'bg-warning-500/20' },
  urgent: { label: 'Urgent', color: 'text-danger-400', bgColor: 'bg-danger-500/20' },
};

export default function RequestCard({ request }: RequestCardProps) {
  const status = statusConfig[request.status] || statusConfig.new;
  const priority = priorityConfig[request.priority] || priorityConfig.medium;

  return (
    <Link
      to={`/requests/${request.id}`}
      className="group block bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 hover:border-tronas-500/50 transition-all duration-200 hover:shadow-glow"
    >
      <div className="p-5">
        {/* Header with Status Badges */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${status.bgColor} ${status.color} border ${status.borderColor}`}>
              {status.label}
            </span>
            <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${priority.bgColor} ${priority.color}`}>
              {priority.label}
            </span>
          </div>
          <DeadlineIndicator deadline={request.response_deadline} compact />
        </div>

        {/* Request Number & Title */}
        <div className="mb-3">
          <span className="text-xs text-navy-500 font-mono">{request.request_number}</span>
          <h3 className="text-base font-semibold text-white group-hover:text-tronas-400 transition-colors line-clamp-1 mt-0.5">
            {request.description?.slice(0, 60) || 'PIA Request'}...
          </h3>
        </div>

        {/* Description Preview */}
        <p className="text-sm text-navy-400 line-clamp-2 mb-4">
          {request.description || 'No description provided'}
        </p>

        {/* Stats Row */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-1.5 text-xs text-navy-500">
            <DocumentTextIcon className="w-4 h-4" />
            <span>{request.total_documents || 0} docs</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-navy-500">
            <FolderIcon className="w-4 h-4" />
            <span>{request.total_pages || 0} pages</span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-navy-800">
          <div className="flex items-center gap-2 text-xs text-navy-500">
            <UserIcon className="h-4 w-4" />
            <span className="truncate max-w-[120px]">{request.requester_name}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-navy-500">
            <ClockIcon className="h-4 w-4" />
            <span>{format(new Date(request.date_received || request.created_at), 'MMM d')}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
