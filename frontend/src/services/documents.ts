import api from './api';

export interface Document {
  id: string;
  request_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  classification: 'public' | 'confidential' | 'restricted' | 'unclassified';
  redaction_required: boolean;
  status: 'pending' | 'classified' | 'redacted' | 'approved' | 'released';
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export const documentsService = {
  // Get all documents with optional filters
  getDocuments: async (params?: {
    request_id?: string;
    classification?: string;
    status?: string;
    page?: number;
    limit?: number;
  }) => {
    const response = await api.get('/documents', { params });
    return response.data;
  },

  // Get single document
  getDocument: async (id: string) => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  // Upload document
  uploadDocument: async (formData: FormData) => {
    const response = await api.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Classify document
  classifyDocument: async (id: string) => {
    const response = await api.post(`/documents/${id}/classify`);
    return response.data;
  },

  // Update document metadata
  updateDocument: async (id: string, data: Partial<Document>) => {
    const response = await api.put(`/documents/${id}`, data);
    return response.data;
  },

  // Download document
  downloadDocument: async (id: string) => {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Delete document
  deleteDocument: async (id: string) => {
    const response = await api.delete(`/documents/${id}`);
    return response.data;
  },
};

export default documentsService;
