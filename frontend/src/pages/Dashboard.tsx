import { Link } from 'react-router-dom';
import { useDashboardOverview, useUrgentItems } from '../hooks/useDashboard';
import {
  ClipboardDocumentListIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  BoltIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: number;
  color: 'tronas' | 'warning' | 'danger' | 'success' | 'purple';
  subtitle?: string;
}

function StatCard({ title, value, icon, trend, color, subtitle }: StatCardProps) {
  const colorClasses = {
    tronas: 'from-tronas-500/20 to-tronas-600/20 border-tronas-500/30 text-tronas-400',
    warning: 'from-warning-500/20 to-warning-600/20 border-warning-500/30 text-warning-400',
    danger: 'from-danger-500/20 to-danger-600/20 border-danger-500/30 text-danger-400',
    success: 'from-success-500/20 to-success-600/20 border-success-500/30 text-success-500',
    purple: 'from-purple-500/20 to-purple-600/20 border-purple-500/30 text-purple-400',
  };

  const iconBgClasses = {
    tronas: 'bg-tronas-500/20 text-tronas-400',
    warning: 'bg-warning-500/20 text-warning-400',
    danger: 'bg-danger-500/20 text-danger-400',
    success: 'bg-success-500/20 text-success-500',
    purple: 'bg-purple-500/20 text-purple-400',
  };

  return (
    <div className={`
      relative overflow-hidden rounded-2xl p-6
      bg-gradient-to-br ${colorClasses[color].split(' ')[0]} ${colorClasses[color].split(' ')[1]}
      border ${colorClasses[color].split(' ')[2]}
      backdrop-blur-xl
      transition-all duration-300 hover:scale-[1.02] hover:shadow-glow
    `}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-navy-400 text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          {subtitle && (
            <p className="text-navy-400 text-xs mt-1">{subtitle}</p>
          )}
          {trend !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${trend >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
              <ArrowTrendingUpIcon className={`w-4 h-4 ${trend < 0 ? 'rotate-180' : ''}`} />
              <span>{Math.abs(trend)}% from last week</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl ${iconBgClasses[color]}`}>
          {icon}
        </div>
      </div>

      {/* Decorative gradient blob */}
      <div className={`absolute -bottom-10 -right-10 w-32 h-32 rounded-full blur-3xl opacity-20 ${colorClasses[color].split(' ').pop()?.replace('text', 'bg')}`} />
    </div>
  );
}

interface UrgentItemCardProps {
  item: {
    id: number;
    title: string;
    description: string;
    type: string;
    priority: string;
    deadline: string;
    requester: string;
    status: string;
    days_remaining?: number;
    days_overdue?: number;
  };
}

function UrgentItemCard({ item }: UrgentItemCardProps) {
  const isOverdue = item.type === 'overdue_request';

  return (
    <Link
      to={`/requests/${item.id}`}
      className="block p-4 rounded-xl bg-navy-800/50 border border-navy-700 hover:border-tronas-500/50 hover:bg-navy-800 transition-all duration-200 group"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {isOverdue ? (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-danger-500/20 text-danger-400 border border-danger-500/30">
              Overdue
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-warning-500/20 text-warning-400 border border-warning-500/30">
              Urgent
            </span>
          )}
          <span className="text-navy-400 text-xs">
            {item.status.replace(/_/g, ' ')}
          </span>
        </div>
        <span className={`text-sm font-mono ${isOverdue ? 'text-danger-400' : 'text-warning-400'}`}>
          {isOverdue ? `-${item.days_overdue}d` : `${item.days_remaining}d`}
        </span>
      </div>
      <h4 className="text-white font-medium group-hover:text-tronas-400 transition-colors">
        {item.title}
      </h4>
      <p className="text-navy-400 text-sm mt-1 line-clamp-2">
        {item.description}
      </p>
      <div className="flex items-center gap-2 mt-3 text-xs text-navy-500">
        <span>{item.requester}</span>
        <span>•</span>
        <span>{new Date(item.deadline).toLocaleDateString()}</span>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const { data: overview, isLoading: overviewLoading } = useDashboardOverview();
  const { data: urgentItems, isLoading: urgentLoading } = useUrgentItems();

  if (overviewLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-tronas-500/20 flex items-center justify-center animate-pulse">
            <SparklesIcon className="w-6 h-6 text-tronas-400" />
          </div>
          <p className="text-navy-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white">
            Welcome to Tronas
          </h1>
          <p className="text-navy-400 mt-1">
            AI-powered PIA automation for the City of San Antonio
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 bg-tronas-500/10 border border-tronas-500/30 rounded-xl">
            <BoltIcon className="w-5 h-5 text-tronas-400" />
            <span className="text-tronas-400 text-sm font-medium">AI Active</span>
          </div>
        </div>
      </div>

      {/* Primary Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Requests"
          value={overview?.total_requests || 0}
          icon={<ClipboardDocumentListIcon className="w-6 h-6" />}
          color="tronas"
          trend={12}
        />
        <StatCard
          title="In Progress"
          value={overview?.in_progress_requests || 0}
          icon={<ClockIcon className="w-6 h-6" />}
          color="warning"
          subtitle="Active processing"
        />
        <StatCard
          title="Completed"
          value={overview?.completed_requests || 0}
          icon={<CheckCircleIcon className="w-6 h-6" />}
          color="success"
          trend={8}
        />
        <StatCard
          title="Urgent"
          value={overview?.urgent_requests || 0}
          icon={<ExclamationTriangleIcon className="w-6 h-6" />}
          color="danger"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Pending Review"
          value={overview?.pending_requests || 0}
          icon={<DocumentTextIcon className="w-6 h-6" />}
          color="purple"
        />
        <StatCard
          title="Documents Processed"
          value={(overview?.documents_processed || 0).toLocaleString()}
          icon={<DocumentTextIcon className="w-6 h-6" />}
          color="tronas"
          subtitle="All time"
        />
        <StatCard
          title="Avg Processing Time"
          value={`${overview?.avg_processing_time || 0}d`}
          icon={<ChartBarIcon className="w-6 h-6" />}
          color="success"
          subtitle="Target: 10 days"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Urgent Items */}
        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-danger-500/20">
                <ExclamationTriangleIcon className="w-5 h-5 text-danger-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Urgent Items</h3>
            </div>
            <Link
              to="/requests?status=urgent"
              className="text-sm text-tronas-400 hover:text-tronas-300 transition-colors"
            >
              View all
            </Link>
          </div>

          {urgentLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-pulse text-navy-400">Loading...</div>
            </div>
          ) : urgentItems && urgentItems.length > 0 ? (
            <div className="space-y-3">
              {urgentItems.slice(0, 4).map((item: any) => (
                <UrgentItemCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-3 rounded-xl bg-success-500/10 mb-3">
                <ShieldCheckIcon className="w-8 h-8 text-success-500" />
              </div>
              <p className="text-navy-300 font-medium">All caught up!</p>
              <p className="text-navy-500 text-sm">No urgent items at this time</p>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-tronas-500/20">
                <SparklesIcon className="w-5 h-5 text-tronas-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
            </div>
          </div>

          {overview?.recent_activity && overview.recent_activity.length > 0 ? (
            <div className="space-y-4">
              {overview.recent_activity.slice(0, 5).map((activity: any, index: number) => (
                <div
                  key={activity.id || index}
                  className="flex gap-3 pb-4 border-b border-navy-800 last:border-0 last:pb-0"
                >
                  <div className="relative">
                    <div className="w-2 h-2 mt-2 rounded-full bg-tronas-500 shadow-glow" />
                    {index < 4 && (
                      <div className="absolute top-3 left-[3px] w-0.5 h-full bg-navy-700" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-navy-200">
                      {activity.description}
                    </p>
                    <p className="text-xs text-navy-500 mt-1">
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-navy-400">No recent activity</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link
            to="/requests/new"
            className="group flex items-center gap-4 p-4 rounded-xl border-2 border-dashed border-navy-700 hover:border-tronas-500 hover:bg-tronas-500/5 transition-all"
          >
            <div className="p-3 rounded-lg bg-tronas-500/10 group-hover:bg-tronas-500/20 transition-colors">
              <ClipboardDocumentListIcon className="w-6 h-6 text-tronas-400" />
            </div>
            <div>
              <span className="font-medium text-white block">New Request</span>
              <span className="text-sm text-navy-400">Create PIA request</span>
            </div>
          </Link>
          <Link
            to="/requests?status=pending_department_review"
            className="group flex items-center gap-4 p-4 rounded-xl border-2 border-dashed border-navy-700 hover:border-warning-500 hover:bg-warning-500/5 transition-all"
          >
            <div className="p-3 rounded-lg bg-warning-500/10 group-hover:bg-warning-500/20 transition-colors">
              <ClockIcon className="w-6 h-6 text-warning-400" />
            </div>
            <div>
              <span className="font-medium text-white block">Pending Review</span>
              <span className="text-sm text-navy-400">Needs your attention</span>
            </div>
          </Link>
          <Link
            to="/analytics"
            className="group flex items-center gap-4 p-4 rounded-xl border-2 border-dashed border-navy-700 hover:border-purple-500 hover:bg-purple-500/5 transition-all"
          >
            <div className="p-3 rounded-lg bg-purple-500/10 group-hover:bg-purple-500/20 transition-colors">
              <ChartBarIcon className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <span className="font-medium text-white block">Analytics</span>
              <span className="text-sm text-navy-400">View insights</span>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
