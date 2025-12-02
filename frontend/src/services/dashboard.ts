import api from './api';

export interface DashboardOverview {
  total_requests: number;
  pending_requests: number;
  in_progress_requests: number;
  completed_requests: number;
  urgent_requests: number;
  overdue_requests: number;
  avg_processing_time: number;
  documents_processed: number;
  recent_activity: Array<{
    id: string;
    type: string;
    description: string;
    timestamp: string;
  }>;
}

export interface UrgentItem {
  id: string;
  type: 'request' | 'task' | 'document';
  title: string;
  description: string;
  priority: string;
  deadline: string;
  status: string;
}

export const dashboardService = {
  // Get dashboard overview
  getOverview: async () => {
    const response = await api.get('/dashboard/overview');
    return response.data;
  },

  // Get urgent items
  getUrgentItems: async () => {
    const response = await api.get('/dashboard/urgent-items');
    return response.data;
  },
};

export default dashboardService;
