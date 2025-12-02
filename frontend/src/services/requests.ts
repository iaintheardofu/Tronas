import api from './api';

export interface PIARequest {
  id: number;
  request_number: string;
  requester_name: string;
  requester_email: string;
  requester_phone?: string;
  requester_organization?: string;
  description: string;
  status: 'new' | 'acknowledged' | 'in_progress' | 'pending_department_review' | 'pending_ag_ruling' | 'released' | 'closed_no_records' | 'withdrawn';
  request_type: 'standard' | 'expedited' | 'recurring' | 'media' | 'legal';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  date_received: string;
  response_deadline: string;
  extension_deadline?: string;
  total_documents: number;
  total_pages: number;
  responsive_documents: number;
  created_at: string;
  updated_at: string;
  assigned_to?: number;
}

export interface CreateRequestData {
  requester_name: string;
  requester_email: string;
  requester_phone?: string;
  requester_organization?: string;
  description: string;
  request_type?: string;
  priority?: string;
  delivery_method?: string;
}

export const requestsService = {
  // Get all requests with optional filters
  getRequests: async (params?: {
    status?: string;
    priority?: string;
    page?: number;
    limit?: number;
  }) => {
    const response = await api.get('/requests', { params });
    return response.data;
  },

  // Get single request by ID
  getRequest: async (id: string) => {
    const response = await api.get(`/requests/${id}`);
    return response.data;
  },

  // Create new request
  createRequest: async (data: CreateRequestData) => {
    const response = await api.post('/requests', data);
    return response.data;
  },

  // Update request
  updateRequest: async (id: string, data: Partial<PIARequest>) => {
    const response = await api.put(`/requests/${id}`, data);
    return response.data;
  },

  // Start automated processing
  startProcessing: async (id: string) => {
    const response = await api.post(`/requests/${id}/start-processing`);
    return response.data;
  },

  // Delete request
  deleteRequest: async (id: string) => {
    const response = await api.delete(`/requests/${id}`);
    return response.data;
  },
};

export default requestsService;
