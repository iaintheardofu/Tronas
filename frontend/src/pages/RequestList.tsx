import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useRequests } from '../hooks/useRequests';
import RequestCard from '../components/RequestCard';
import {
  PlusCircleIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ClipboardDocumentListIcon,
  SparklesIcon,
  XMarkIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'pending_department_review', label: 'Pending Review' },
  { value: 'pending_ag_ruling', label: 'Pending AG Ruling' },
  { value: 'released', label: 'Released' },
  { value: 'closed_no_records', label: 'Closed - No Records' },
];

const priorityOptions = [
  { value: '', label: 'All Priorities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
];

export default function RequestList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const status = searchParams.get('status') || '';
  const priority = searchParams.get('priority') || '';

  const { data: requests, isLoading, error } = useRequests({
    status: status || undefined,
    priority: priority || undefined,
  });

  const handleFilterChange = (key: string, value: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchParams({});
  };

  const hasActiveFilters = status || priority;

  // Filter requests by search query
  const filteredRequests = requests?.filter((request: any) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      request.request_number?.toLowerCase().includes(query) ||
      request.requester_name?.toLowerCase().includes(query) ||
      request.description?.toLowerCase().includes(query)
    );
  });

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white">
            PIA Requests
          </h1>
          <p className="text-navy-400 mt-1">
            Manage and track all public information requests
          </p>
        </div>

        <Link
          to="/requests/new"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white font-medium rounded-xl shadow-glow transition-all duration-200"
        >
          <PlusCircleIcon className="h-5 w-5" />
          New Request
        </Link>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-500" />
            <input
              type="text"
              placeholder="Search by request number, requester, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
            />
          </div>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
              showFilters || hasActiveFilters
                ? 'bg-tronas-500/20 text-tronas-400 border border-tronas-500/30'
                : 'bg-navy-800/50 text-navy-400 border border-navy-700 hover:text-white hover:border-navy-600'
            }`}
          >
            <AdjustmentsHorizontalIcon className="w-5 h-5" />
            Filters
            {hasActiveFilters && (
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-tronas-500 text-white text-xs">
                {[status, priority].filter(Boolean).length}
              </span>
            )}
          </button>
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-navy-700 grid grid-cols-1 md:grid-cols-3 gap-4 animate-slide-down">
            <div>
              <label className="block text-sm font-medium text-navy-400 mb-2">
                Status
              </label>
              <select
                value={status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full px-4 py-2.5 bg-navy-800/50 border border-navy-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value} className="bg-navy-900">
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-navy-400 mb-2">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => handleFilterChange('priority', e.target.value)}
                className="w-full px-4 py-2.5 bg-navy-800/50 border border-navy-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
              >
                {priorityOptions.map((option) => (
                  <option key={option.value} value={option.value} className="bg-navy-900">
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="flex items-center gap-2 px-4 py-2.5 text-navy-400 hover:text-white font-medium transition-colors"
              >
                <XMarkIcon className="w-4 h-4" />
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results Summary */}
      {filteredRequests && (
        <div className="flex items-center gap-2 text-sm text-navy-400">
          <span className="font-medium text-white">{filteredRequests.length}</span>
          <span>requests found</span>
          {hasActiveFilters && (
            <>
              <span className="text-navy-600">•</span>
              <span>Filtered</span>
            </>
          )}
        </div>
      )}

      {/* Request List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-tronas-500/20 flex items-center justify-center animate-pulse">
              <SparklesIcon className="w-6 h-6 text-tronas-400" />
            </div>
            <p className="text-navy-400">Loading requests...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-danger-500/10 border border-danger-500/30 rounded-2xl p-6 text-center">
          <p className="text-danger-400">Error loading requests. Please try again.</p>
        </div>
      ) : filteredRequests && filteredRequests.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredRequests.map((request: any) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </div>
      ) : (
        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-4 rounded-2xl bg-navy-800/50">
              <ClipboardDocumentListIcon className="h-12 w-12 text-navy-600" />
            </div>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">
            No requests found
          </h3>
          <p className="text-navy-400 mb-6 max-w-sm mx-auto">
            {hasActiveFilters
              ? 'Try adjusting your filters to find what you\'re looking for'
              : 'Get started by creating your first PIA request'
            }
          </p>
          {hasActiveFilters ? (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy-800 hover:bg-navy-700 text-white rounded-xl font-medium transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
              Clear Filters
            </button>
          ) : (
            <Link
              to="/requests/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white rounded-xl font-medium shadow-glow transition-all duration-200"
            >
              <PlusCircleIcon className="h-5 w-5" />
              New Request
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
