import { useParams, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { useRequest, useStartProcessing } from '../hooks/useRequests';
import { useDocuments, useClassifyDocument, useDeleteDocument } from '../hooks/useDocuments';
import { useWorkflowStatus } from '../hooks/useWorkflow';
import DocumentTable from '../components/DocumentTable';
import WorkflowProgress from '../components/WorkflowProgress';
import DeadlineIndicator from '../components/DeadlineIndicator';
import {
  ArrowLeftIcon,
  PlayIcon,
  UserIcon,
  EnvelopeIcon,
  CalendarIcon,
  ClockIcon,
  DocumentTextIcon,
  FolderIcon,
  SparklesIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PauseIcon,
  CloudArrowUpIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

const statusConfig: Record<string, { label: string; color: string; bgColor: string; borderColor: string }> = {
  new: { label: 'New', color: 'text-tronas-400', bgColor: 'bg-tronas-500/20', borderColor: 'border-tronas-500/30' },
  in_progress: { label: 'In Progress', color: 'text-warning-400', bgColor: 'bg-warning-500/20', borderColor: 'border-warning-500/30' },
  pending_department_review: { label: 'Pending Review', color: 'text-purple-400', bgColor: 'bg-purple-500/20', borderColor: 'border-purple-500/30' },
  pending_ag_ruling: { label: 'Pending AG Ruling', color: 'text-warning-400', bgColor: 'bg-warning-500/20', borderColor: 'border-warning-500/30' },
  released: { label: 'Released', color: 'text-success-500', bgColor: 'bg-success-500/20', borderColor: 'border-success-500/30' },
  closed_no_records: { label: 'Closed - No Records', color: 'text-navy-400', bgColor: 'bg-navy-500/20', borderColor: 'border-navy-500/30' },
  withdrawn: { label: 'Withdrawn', color: 'text-navy-400', bgColor: 'bg-navy-500/20', borderColor: 'border-navy-500/30' },
};

const priorityConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  low: { label: 'Low', color: 'text-navy-400', bgColor: 'bg-navy-500/20' },
  medium: { label: 'Medium', color: 'text-tronas-400', bgColor: 'bg-tronas-500/20' },
  high: { label: 'High', color: 'text-warning-400', bgColor: 'bg-warning-500/20' },
  urgent: { label: 'Urgent', color: 'text-danger-400', bgColor: 'bg-danger-500/20' },
};

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: request, isLoading: requestLoading } = useRequest(id!);
  const { data: documents, isLoading: documentsLoading } = useDocuments({
    request_id: id,
  });
  const { data: workflow } = useWorkflowStatus(id!);

  const startProcessing = useStartProcessing();
  const classifyDocument = useClassifyDocument();
  const deleteDocument = useDeleteDocument();

  if (requestLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-tronas-500/20 flex items-center justify-center animate-pulse">
            <SparklesIcon className="w-6 h-6 text-tronas-400" />
          </div>
          <p className="text-navy-400">Loading request details...</p>
        </div>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="bg-danger-500/10 border border-danger-500/30 rounded-2xl p-8 text-center">
        <ExclamationTriangleIcon className="w-12 h-12 text-danger-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">Request Not Found</h3>
        <p className="text-navy-400 mb-6">The request you're looking for doesn't exist or has been removed.</p>
        <button
          onClick={() => navigate('/requests')}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy-800 hover:bg-navy-700 text-white rounded-xl font-medium transition-colors"
        >
          <ArrowLeftIcon className="w-5 h-5" />
          Back to Requests
        </button>
      </div>
    );
  }

  const handleStartProcessing = () => {
    if (id) {
      startProcessing.mutate(id);
    }
  };

  const handleClassify = (docId: string) => {
    classifyDocument.mutate(docId);
  };

  const handleDelete = (docId: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      deleteDocument.mutate(docId);
    }
  };

  const status = statusConfig[request.status] || statusConfig.new;
  const priority = priorityConfig[request.priority] || priorityConfig.medium;

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div className="flex items-start gap-4">
          <button
            onClick={() => navigate('/requests')}
            className="p-2.5 text-navy-400 hover:text-white hover:bg-navy-800 rounded-xl transition-colors mt-1"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className={`px-3 py-1 rounded-lg text-sm font-medium ${status.bgColor} ${status.color} border ${status.borderColor}`}>
                {status.label}
              </span>
              <span className={`px-3 py-1 rounded-lg text-sm font-medium ${priority.bgColor} ${priority.color}`}>
                {priority.label} Priority
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">
              Request {request.request_number}
            </h1>
            <p className="text-navy-400 mt-1">
              {request.requester_name} • Submitted {format(new Date(request.date_received), 'MMM d, yyyy')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-14 lg:ml-0">
          {request.status !== 'released' && request.status !== 'closed_no_records' && (
            <button
              onClick={handleStartProcessing}
              disabled={startProcessing.isPending}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white font-medium rounded-xl shadow-glow transition-all duration-200 disabled:opacity-50"
            >
              {startProcessing.isPending ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Processing...
                </>
              ) : request.status === 'new' ? (
                <>
                  <PlayIcon className="h-5 w-5" />
                  Start Processing
                </>
              ) : (
                <>
                  <ArrowPathIcon className="h-5 w-5" />
                  Resume Processing
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-tronas-500/20">
              <DocumentTextIcon className="w-5 h-5 text-tronas-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{request.total_documents || 0}</p>
              <p className="text-sm text-navy-400">Documents</p>
            </div>
          </div>
        </div>

        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success-500/20">
              <CheckCircleIcon className="w-5 h-5 text-success-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{request.responsive_documents || 0}</p>
              <p className="text-sm text-navy-400">Responsive</p>
            </div>
          </div>
        </div>

        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning-500/20">
              <FolderIcon className="w-5 h-5 text-warning-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{request.total_pages || 0}</p>
              <p className="text-sm text-navy-400">Total Pages</p>
            </div>
          </div>
        </div>

        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-danger-500/20">
              <ClockIcon className="w-5 h-5 text-danger-400" />
            </div>
            <div>
              <DeadlineIndicator deadline={request.response_deadline} compact />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Request Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Request Information */}
          <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <DocumentTextIcon className="w-5 h-5 text-tronas-400" />
              Request Details
            </h2>
            <div className="prose prose-invert max-w-none">
              <p className="text-navy-300 whitespace-pre-wrap leading-relaxed">
                {request.description}
              </p>
            </div>
          </div>

          {/* Workflow Progress */}
          {workflow && (
            <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <ChartBarIcon className="w-5 h-5 text-tronas-400" />
                Workflow Progress
              </h2>
              <WorkflowProgress workflow={workflow} />
            </div>
          )}

          {/* Documents Section */}
          <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FolderIcon className="w-5 h-5 text-tronas-400" />
                Documents
              </h2>
              <button className="flex items-center gap-2 px-4 py-2 bg-navy-800 hover:bg-navy-700 text-white rounded-xl font-medium transition-colors">
                <CloudArrowUpIcon className="w-5 h-5" />
                Upload
              </button>
            </div>

            {documentsLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex flex-col items-center gap-3">
                  <ArrowPathIcon className="w-8 h-8 text-tronas-400 animate-spin" />
                  <p className="text-navy-400">Loading documents...</p>
                </div>
              </div>
            ) : documents && documents.length > 0 ? (
              <DocumentTable
                documents={documents}
                onClassify={handleClassify}
                onDelete={handleDelete}
              />
            ) : (
              <div className="text-center py-12">
                <FolderIcon className="w-12 h-12 text-navy-600 mx-auto mb-4" />
                <p className="text-navy-400 mb-2">No documents yet</p>
                <p className="text-navy-500 text-sm">Upload documents or start processing to retrieve them automatically</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Sidebar */}
        <div className="space-y-6">
          {/* Requester Info */}
          <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
            <h3 className="text-sm font-semibold text-navy-400 uppercase tracking-wider mb-4">
              Requester Information
            </h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-navy-800">
                  <UserIcon className="w-4 h-4 text-navy-400" />
                </div>
                <div>
                  <p className="text-sm text-navy-500">Name</p>
                  <p className="text-white font-medium">{request.requester_name}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-navy-800">
                  <EnvelopeIcon className="w-4 h-4 text-navy-400" />
                </div>
                <div>
                  <p className="text-sm text-navy-500">Email</p>
                  <a href={`mailto:${request.requester_email}`} className="text-tronas-400 hover:text-tronas-300 font-medium">
                    {request.requester_email}
                  </a>
                </div>
              </div>

              {request.requester_phone && (
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-navy-800">
                    <svg className="w-4 h-4 text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-navy-500">Phone</p>
                    <p className="text-white font-medium">{request.requester_phone}</p>
                  </div>
                </div>
              )}

              {request.requester_organization && (
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-navy-800">
                    <svg className="w-4 h-4 text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-navy-500">Organization</p>
                    <p className="text-white font-medium">{request.requester_organization}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
            <h3 className="text-sm font-semibold text-navy-400 uppercase tracking-wider mb-4">
              Key Dates
            </h3>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-tronas-500" />
                <div className="flex-1">
                  <p className="text-sm text-navy-500">Received</p>
                  <p className="text-white font-medium">
                    {format(new Date(request.date_received), 'MMM d, yyyy')}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${request.is_overdue ? 'bg-danger-500' : 'bg-warning-500'}`} />
                <div className="flex-1">
                  <p className="text-sm text-navy-500">Response Deadline</p>
                  <p className={`font-medium ${request.is_overdue ? 'text-danger-400' : 'text-white'}`}>
                    {format(new Date(request.response_deadline), 'MMM d, yyyy')}
                  </p>
                </div>
              </div>

              {request.extension_deadline && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <div className="flex-1">
                    <p className="text-sm text-navy-500">Extension Deadline</p>
                    <p className="text-white font-medium">
                      {format(new Date(request.extension_deadline), 'MMM d, yyyy')}
                    </p>
                  </div>
                </div>
              )}

              {request.date_completed && (
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-success-500" />
                  <div className="flex-1">
                    <p className="text-sm text-navy-500">Completed</p>
                    <p className="text-success-500 font-medium">
                      {format(new Date(request.date_completed), 'MMM d, yyyy')}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* AI Processing Info */}
          <div className="bg-gradient-to-br from-tronas-500/10 to-tronas-600/10 backdrop-blur-xl rounded-2xl border border-tronas-500/30 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-tronas-500/20">
                <SparklesIcon className="w-5 h-5 text-tronas-400" />
              </div>
              <h3 className="text-sm font-semibold text-tronas-400 uppercase tracking-wider">
                AI Processing
              </h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-navy-400">Classification</span>
                <span className={request.classification_complete ? 'text-success-500' : 'text-warning-400'}>
                  {request.classification_complete ? 'Complete' : 'Pending'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-navy-400">Deduplication</span>
                <span className={request.deduplication_complete ? 'text-success-500' : 'text-warning-400'}>
                  {request.deduplication_complete ? 'Complete' : 'Pending'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-navy-400">OCR Status</span>
                <span className={request.ocr_complete ? 'text-success-500' : 'text-warning-400'}>
                  {request.ocr_complete ? 'Complete' : 'Pending'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
