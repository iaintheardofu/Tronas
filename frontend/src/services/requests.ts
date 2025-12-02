import api from './api';

export interface PIARequest {
  id: string;
  requester_name: string;
  requester_email: string;
  request_subject: string;
  request_details: string;
  status: 'pending' | 'in_progress' | 'completed' | 'requires_review';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  deadline: string;
  created_at: string;
  updated_at: string;
  assigned_to?: string;
  estimated_completion?: string;
}

export interface CreateRequestData {
  requester_name: string;
  requester_email: string;
  request_subject: string;
  request_details: string;
  priority?: string;
  deadline?: string;
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
