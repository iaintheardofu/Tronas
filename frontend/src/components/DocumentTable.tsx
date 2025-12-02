import { format } from 'date-fns';
import { Document } from '../services/documents';
import ClassificationBadge from './ClassificationBadge';
import {
  DocumentIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  SparklesIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';

interface DocumentTableProps {
  documents: Document[];
  onDownload?: (id: string) => void;
  onDelete?: (id: string) => void;
  onClassify?: (id: string) => void;
}

const statusConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  pending: { label: 'Pending', color: 'text-navy-400', bgColor: 'bg-navy-500/20' },
  processing: { label: 'Processing', color: 'text-warning-400', bgColor: 'bg-warning-500/20' },
  classified: { label: 'Classified', color: 'text-tronas-400', bgColor: 'bg-tronas-500/20' },
  reviewed: { label: 'Reviewed', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  redacted: { label: 'Redacted', color: 'text-warning-400', bgColor: 'bg-warning-500/20' },
  approved: { label: 'Approved', color: 'text-success-500', bgColor: 'bg-success-500/20' },
  released: { label: 'Released', color: 'text-success-500', bgColor: 'bg-success-500/20' },
  withheld: { label: 'Withheld', color: 'text-danger-400', bgColor: 'bg-danger-500/20' },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getFileIcon(fileType: string) {
  const type = fileType?.toLowerCase() || '';
  if (type.includes('pdf')) return 'bg-danger-500/20 text-danger-400';
  if (type.includes('doc') || type.includes('word')) return 'bg-tronas-500/20 text-tronas-400';
  if (type.includes('xls') || type.includes('excel')) return 'bg-success-500/20 text-success-500';
  if (type.includes('image') || type.includes('png') || type.includes('jpg')) return 'bg-purple-500/20 text-purple-400';
  if (type.includes('email') || type.includes('msg')) return 'bg-warning-500/20 text-warning-400';
  return 'bg-navy-500/20 text-navy-400';
}

export default function DocumentTable({
  documents,
  onDownload,
  onDelete,
  onClassify,
}: DocumentTableProps) {
  return (
    <div className="overflow-hidden rounded-xl border border-navy-700">
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="bg-navy-800/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Document
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Classification
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Size
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Added
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-navy-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-800">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-navy-500">
                  No documents found
                </td>
              </tr>
            ) : (
              documents.map((doc) => {
                const status = statusConfig[doc.status] || statusConfig.pending;
                const iconColor = getFileIcon(doc.file_type || 'unknown');

                return (
                  <tr key={doc.id} className="hover:bg-navy-800/30 transition-colors">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${iconColor}`}>
                          <DocumentIcon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white truncate max-w-[200px]">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-navy-500">
                            {doc.file_type} • {doc.page_count || 1} page{(doc.page_count || 1) > 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <ClassificationBadge classification={doc.classification} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${status.bgColor} ${status.color}`}>
                        {status.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-navy-400">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-navy-400">
                      {format(new Date(doc.created_at), 'MMM d')}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <div className="flex justify-end gap-1">
                        {doc.status === 'pending' && onClassify && (
                          <button
                            onClick={() => onClassify(String(doc.id))}
                            className="p-2 text-tronas-400 hover:text-tronas-300 hover:bg-tronas-500/20 rounded-lg transition-colors"
                            title="Classify with AI"
                          >
                            <SparklesIcon className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          className="p-2 text-navy-400 hover:text-white hover:bg-navy-700 rounded-lg transition-colors"
                          title="Preview"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        {onDownload && (
                          <button
                            onClick={() => onDownload(String(doc.id))}
                            className="p-2 text-navy-400 hover:text-white hover:bg-navy-700 rounded-lg transition-colors"
                            title="Download"
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                          </button>
                        )}
                        {onDelete && (
                          <button
                            onClick={() => onDelete(String(doc.id))}
                            className="p-2 text-navy-400 hover:text-danger-400 hover:bg-danger-500/20 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
